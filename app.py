from flask import Flask, render_template, request, jsonify
from amap_mcp_client import (
    AmapMCPClient, parse_geocode, parse_poi_list, 
    parse_weather, haversine_distance, estimate_travel_time, greedy_tsp
)
import math
import random
from datetime import datetime, timedelta

app = Flask(__name__)


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/test_key', methods=['POST'])
def test_key():
    try:
        data = request.get_json()
        api_key = data.get('api_key', '').strip()
        
        if not api_key:
            return jsonify({'ok': False, 'message': '请提供API Key'})
        
        client = AmapMCPClient(api_key)
        result = client.geocode('北京')
        
        if result and result.get('status') == '1':
            return jsonify({'ok': True, 'message': 'API Key有效'})
        else:
            info = result.get('info', '未知错误') if result else '无响应'
            return jsonify({'ok': False, 'message': f'API Key无效: {info}'})
    except Exception as e:
        return jsonify({'ok': False, 'message': f'测试失败: {str(e)}'})


@app.route('/plan', methods=['POST'])
def plan():
    try:
        data = request.get_json()
        city = data.get('city', '').strip()
        days = int(data.get('days', 3))
        spots_per_day = int(data.get('spots_per_day', 4))
        api_key = data.get('api_key', '').strip()
        start_date = data.get('start_date', '')
        plan_type = data.get('plan_type', 'balanced')
        
        if days < 1 or days > 7:
            return jsonify({'ok': False, 'message': '出行天数需在1-7天之间'})
        
        if spots_per_day < 1 or spots_per_day > 5:
            return jsonify({'ok': False, 'message': '每天景点数需在1-5之间'})
        
        if not city or not api_key:
            return jsonify({'ok': False, 'message': '请填写城市和API Key'})
        
        client = AmapMCPClient(api_key)
        
        geo_result = client.geocode(city)
        geo_data = parse_geocode(geo_result)
        
        if not geo_data or not geo_data.get('location'):
            return jsonify({'ok': False, 'message': f'无法获取{city}的地理坐标'})
        
        center_location = geo_data['location']
        
        weather_result = client.weather(city)
        weather_list = parse_weather(weather_result, days)
        
        if start_date:
            try:
                start_dt = datetime.strptime(start_date, '%Y-%m-%d')
                filtered_weather = []
                for w in weather_list:
                    if w.get('date'):
                        try:
                            w_date = datetime.strptime(w['date'], '%Y-%m-%d')
                            if w_date >= start_dt:
                                filtered_weather.append(w)
                        except:
                            pass
                
                while len(filtered_weather) < days and filtered_weather:
                    last = filtered_weather[-1].copy()
                    last['date'] = (start_dt + timedelta(days=len(filtered_weather))).strftime('%Y-%m-%d')
                    filtered_weather.append(last)
                
                weather_list = filtered_weather[:days]
            except:
                pass
        
        spot_keywords_map = {
            'classic': [
                '旅游景点', '风景名胜', '景区', '名胜古迹', '景点', 
                '旅游', '风景区', '著名景点', '必游景点', '热门景点'
            ],
            'cultural': [
                '博物馆', '纪念馆', '古镇', '寺庙', '文化遗址', 
                '历史建筑', '宗教场所', '古迹', '文化景点', '历史景点'
            ],
            'nature': [
                '山', '湖泊', '公园', '湿地', '森林公园', 
                '山水', '自然景观', '风景区', '山水风光', '自然景点'
            ],
            'relax': [
                '公园', '广场', '游乐场', '温泉', '度假村', 
                '休闲景点', '休闲场所', '度假', '娱乐', '休闲'
            ],
            'balanced': [
                '旅游景点', '风景名胜', '景区', '名胜古迹', '公园', 
                '博物馆', '纪念馆', '古镇', '寺庙', '湖泊', 
                '山', '景点', '旅游', '风景区', '文化遗址', 
                '历史建筑', '宗教场所', '广场', '游乐场', '温泉', '湿地'
            ]
        }
        
        spot_keywords = spot_keywords_map.get(plan_type, spot_keywords_map['balanced'])
        
        all_spots = []
        seen_ids = set()
        need_detail_list = []
        
        for keyword in spot_keywords:
            try:
                poi_result = client.search_poi(
                    keyword=keyword,
                    city=city,
                    offset=25
                )
                poi_list = parse_poi_list(poi_result)
                
                for poi in poi_list:
                    if poi['id'] not in seen_ids:
                        seen_ids.add(poi['id'])
                        if poi.get('location'):
                            all_spots.append(poi)
                        else:
                            need_detail_list.append(poi)
            except:
                continue
        
        for poi in need_detail_list:
            try:
                detail_result = client.search_detail(poi['id'])
                if detail_result and 'pois' in detail_result:
                    detail_poi = detail_result['pois'][0]
                    if detail_poi.get('location'):
                        poi['location'] = detail_poi['location']
                        poi['address'] = detail_poi.get('address', poi['address'])
                        poi['tel'] = detail_poi.get('tel', poi['tel'])
                        photos = detail_poi.get('photos', [])
                        if photos and not poi.get('photo'):
                            poi['photo'] = photos[0].get('url', '')
                        if not poi.get('rating'):
                            poi['rating'] = detail_poi.get('biz_ext', {}).get('rating', '')
                        all_spots.append(poi)
            except:
                continue
        
        for spot in all_spots:
            score = 0
            if spot.get('rating'):
                try:
                    score += float(spot['rating']) * 10
                except:
                    score += 30
            else:
                score += 20
            
            if spot.get('photo'):
                score += 30
            
            if spot.get('address'):
                score += 10
            
            type_str = spot.get('type', '')
            if '5A' in type_str or 'AAAAA' in type_str:
                score += 50
            elif '4A' in type_str or 'AAAA' in type_str:
                score += 40
            elif '3A' in type_str or 'AAA' in type_str:
                score += 30
            
            if any(kw in type_str for kw in ['风景名胜', '公园', '博物馆', '景区']):
                score += 15
            
            spot['score'] = score
        
        all_spots.sort(key=lambda x: x.get('score', 0), reverse=True)
        
        type_count = {}
        diversified_spots = []
        for spot in all_spots:
            type_main = spot.get('type', '').split(';')[0] if spot.get('type') else '其他'
            type_count[type_main] = type_count.get(type_main, 0) + 1
            
            if type_count[type_main] <= 3:
                diversified_spots.append(spot)
            
            if len(diversified_spots) >= days * spots_per_day * 2:
                break
        
        all_spots = diversified_spots if len(diversified_spots) > len(all_spots) * 0.6 else all_spots
        
        spots_with_photo = [s for s in all_spots if s.get('photo')]
        
        actual_days = days
        
        if spots_with_photo:
            total_needed = actual_days * spots_per_day
            if len(spots_with_photo) < total_needed:
                actual_days = max(1, math.ceil(len(spots_with_photo) / spots_per_day))
            all_spots = spots_with_photo
        else:
            actual_days = max(1, math.ceil(len(all_spots) / spots_per_day))
        
        actual_days = min(actual_days, days)
        
        food_keywords = ['特色美食', '当地小吃', '餐厅', '美食']
        food_recommendations = []
        seen_food_ids = set()
        
        for keyword in food_keywords:
            try:
                food_result = client.search_poi(
                    keyword=keyword,
                    city=city,
                    offset=20
                )
                food_list = parse_poi_list(food_result)
                
                for food in food_list:
                    if food['id'] not in seen_food_ids:
                        seen_food_ids.add(food['id'])
                        if food.get('rating') and food.get('photo'):
                            food_recommendations.append(food)
                
                if len(food_recommendations) >= 5:
                    break
            except:
                continue
        
        food_recommendations = food_recommendations[:5]
        
        hotel_keywords = ['酒店', '宾馆', '住宿']
        hotel_recommendations = []
        seen_hotel_ids = set()
        
        for keyword in hotel_keywords:
            try:
                hotel_result = client.search_poi(
                    keyword=keyword,
                    city=city,
                    offset=20
                )
                hotel_list = parse_poi_list(hotel_result)
                
                for hotel in hotel_list:
                    if hotel['id'] not in seen_hotel_ids:
                        seen_hotel_ids.add(hotel['id'])
                        if hotel.get('rating') and hotel.get('photo'):
                            hotel_recommendations.append(hotel)
                
                if len(hotel_recommendations) >= 5:
                    break
            except:
                continue
        
        hotel_recommendations = hotel_recommendations[:5]
        
        if not all_spots:
            return jsonify({'ok': False, 'message': '未找到足够的景点信息'})
        
        daily_plans = []
        spot_index = 0
        
        for day_num in range(actual_days):
            day_spots = []
            for _ in range(spots_per_day):
                if spot_index < len(all_spots):
                    day_spots.append(all_spots[spot_index])
                    spot_index += 1
            
            if not day_spots:
                break
            
            sorted_spots = greedy_tsp(day_spots, center_location)
            
            schedule = []
            current_time = datetime.strptime('08:30', '%H:%M')
            
            for i, spot in enumerate(sorted_spots):
                visit_hours = random.uniform(2.0, 2.5)
                
                if i > 0 and sorted_spots[i-1].get('location') and spot.get('location'):
                    dist = haversine_distance(sorted_spots[i-1]['location'], spot['location'])
                    travel_hours = estimate_travel_time(dist)
                else:
                    travel_hours = 0
                    dist = 0
                
                if travel_hours > 0:
                    travel_time_str = f"{int(travel_hours * 60)}分钟"
                else:
                    travel_time_str = "出发"
                
                if dist > 0:
                    taxi_cost = max(8, int(dist * 3))
                else:
                    taxi_cost = 0
                
                schedule.append({
                    'spot': spot,
                    'time': current_time.strftime('%H:%M'),
                    'visit_hours': round(visit_hours, 1),
                    'travel_time': travel_time_str,
                    'taxi_cost': taxi_cost
                })
                
                current_time += timedelta(hours=visit_hours + travel_hours)
            
            map_url = None
            if len(sorted_spots) >= 2:
                from_loc = sorted_spots[0].get('location', '')
                from_name = sorted_spots[0].get('name', '')
                to_loc = sorted_spots[-1].get('location', '')
                to_name = sorted_spots[-1].get('name', '')
                
                via_points = []
                for spot in sorted_spots[1:-1]:
                    loc = spot.get('location', '')
                    name = spot.get('name', '')
                    if loc:
                        via_points.append(f"{loc},{name}")
                
                via_str = '|'.join(via_points) if via_points else ''
                
                map_url = f"https://uri.amap.com/navigation?from={from_loc},{from_name}&to={to_loc},{to_name}"
                if via_str:
                    map_url += f"&via={via_str}"
                map_url += f"&mode=car&callnative=0&src={city}旅行攻略&policy=0"
            
            daily_plans.append({
                'day': day_num + 1,
                'date': weather_list[day_num]['date'] if day_num < len(weather_list) else '',
                'weather': weather_list[day_num] if day_num < len(weather_list) else {},
                'spots': sorted_spots,
                'schedule': schedule,
                'map_url': map_url
            })
        
        travel_tips = []
        if weather_list:
            avg_temp = 0
            temp_count = 0
            has_rain = False
            
            for w in weather_list:
                try:
                    if w.get('daytemp'):
                        avg_temp += int(w['daytemp'])
                        temp_count += 1
                    if '雨' in w.get('dayweather', '') or '雨' in w.get('nightweather', ''):
                        has_rain = True
                except:
                    pass
            
            if temp_count > 0:
                avg_temp = avg_temp / temp_count
                
                if avg_temp < 10:
                    travel_tips.append('气温较低，建议穿着厚外套或羽绒服')
                elif avg_temp < 20:
                    travel_tips.append('气温适中，建议穿着长袖或薄外套')
                else:
                    travel_tips.append('气温较高，建议穿着轻便透气的衣物')
            
            if has_rain:
                travel_tips.append('出行期间可能有雨，建议携带雨具')
            
            travel_tips.append('建议提前预订酒店和热门景点门票')
            travel_tips.append('出行前检查交通路线和天气变化')
        
        return jsonify({
            'ok': True,
            'city': city,
            'weather': weather_list,
            'daily_plans': daily_plans,
            'food_recommendations': food_recommendations,
            'hotel_recommendations': hotel_recommendations,
            'travel_tips': travel_tips,
            'actual_days': actual_days
        })
        
    except Exception as e:
        return jsonify({'ok': False, 'message': f'规划失败: {str(e)}'})


if __name__ == '__main__':
    app.run(debug=True, port=5000)
