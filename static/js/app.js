let keyTested = false;
let currentApiKey = '';

function setDefaultDate() {
    const today = new Date();
    const tomorrow = new Date(today);
    tomorrow.setDate(tomorrow.getDate() + 1);
    
    const dateInput = document.getElementById('travelDate');
    const minDate = today.toISOString().split('T')[0];
    const defaultDate = tomorrow.toISOString().split('T')[0];
    
    dateInput.min = minDate;
    dateInput.value = defaultDate;
}

setDefaultDate();

document.getElementById('apiKey').addEventListener('input', function() {
    const key = this.value.trim();
    if (key !== currentApiKey) {
        keyTested = false;
        currentApiKey = key;
        const testBtn = document.getElementById('testKeyBtn');
        testBtn.textContent = '测试连接';
        testBtn.className = 'test-btn';
        document.getElementById('keyError').textContent = '';
        document.getElementById('submitBtn').disabled = true;
    }
});

document.getElementById('testKeyBtn').addEventListener('click', async function() {
    const apiKey = document.getElementById('apiKey').value.trim();
    const testBtn = this;
    const keyError = document.getElementById('keyError');
    
    if (!apiKey) {
        keyError.textContent = '请输入API Key';
        return;
    }
    
    testBtn.disabled = true;
    testBtn.textContent = '测试中...';
    keyError.textContent = '';
    
    try {
        const response = await fetch('/test_key', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ api_key: apiKey })
        });
        
        const result = await response.json();
        
        if (result.ok) {
            testBtn.textContent = '测试通过';
            testBtn.className = 'test-btn success';
            keyTested = true;
            document.getElementById('submitBtn').disabled = false;
        } else {
            testBtn.textContent = '测试失败';
            testBtn.className = 'test-btn error';
            keyError.textContent = result.message || 'API Key无效';
            keyTested = false;
        }
    } catch (error) {
        testBtn.textContent = '测试失败';
        testBtn.className = 'test-btn error';
        keyError.textContent = '网络错误，请重试';
        keyTested = false;
    } finally {
        testBtn.disabled = false;
    }
});

document.getElementById('travelForm').addEventListener('submit', async function(e) {
    e.preventDefault();
    
    if (!keyTested) {
        alert('请先测试API Key连接');
        return;
    }
    
    const days = parseInt(document.getElementById('days').value);
    const spotsPerDay = parseInt(document.getElementById('spotsPerDay').value);
    
    if (days < 1 || days > 7) {
        alert('出行天数需在1-7之间');
        return;
    }
    
    if (spotsPerDay < 1 || spotsPerDay > 5) {
        alert('每天游玩景点数需在1-5之间');
        return;
    }
    
    const submitBtn = document.getElementById('submitBtn');
    submitBtn.disabled = true;
    document.getElementById('loadingOverlay').style.display = 'flex';
    
    const progressSteps = [
        { percent: 5, step: '正在解析目的地信息...' },
        { percent: 15, step: '正在获取地理坐标...' },
        { percent: 25, step: '正在查询天气预报...' },
        { percent: 35, step: '正在搜索热门景点...' },
        { percent: 50, step: '正在获取景点详情...' },
        { percent: 60, step: '正在智能排序路线...' },
        { percent: 70, step: '正在规划每日行程...' },
        { percent: 80, step: '正在搜索美食推荐...' },
        { percent: 88, step: '正在搜索住宿推荐...' },
        { percent: 95, step: '正在生成旅行方案...' }
    ];
    
    let progressTimer = null;
    let currentStepIdx = 0;
    const startTime = Date.now();
    const estimatedTotalMs = days * spotsPerDay * 3000 + 8000;
    
    function updateProgress() {
        if (currentStepIdx >= progressSteps.length) return;
        const step = progressSteps[currentStepIdx];
        const fill = document.getElementById('progressFill');
        const percentEl = document.getElementById('progressPercent');
        const timeEl = document.getElementById('progressTime');
        const stepEl = document.getElementById('progressStep');
        
        fill.style.width = step.percent + '%';
        percentEl.textContent = step.percent + '%';
        stepEl.textContent = step.step;
        
        const elapsed = Date.now() - startTime;
        const remainMs = Math.max(0, estimatedTotalMs - elapsed);
        if (remainMs > 0) {
            const secs = Math.ceil(remainMs / 1000);
            timeEl.textContent = '预计剩余 ' + secs + ' 秒';
        } else {
            timeEl.textContent = '即将完成...';
        }
        
        currentStepIdx++;
    }
    
    updateProgress();
    progressTimer = setInterval(updateProgress, 2500);
    
    const formData = {
        api_key: document.getElementById('apiKey').value.trim(),
        city: document.getElementById('city').value.trim(),
        start_date: document.getElementById('travelDate').value,
        days: days,
        spots_per_day: spotsPerDay,
        plan_type: document.getElementById('planType').value
    };
    
    try {
        const response = await fetch('/plan', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(formData)
        });
        
        const result = await response.json();
        
        if (result.ok) {
            renderResult(result);
            document.getElementById('resultSection').style.display = 'block';
        } else {
            alert(result.message || '规划失败，请重试');
        }
    } catch (error) {
        alert('网络错误，请重试');
    } finally {
        clearInterval(progressTimer);
        const fill = document.getElementById('progressFill');
        const percentEl = document.getElementById('progressPercent');
        const timeEl = document.getElementById('progressTime');
        const stepEl = document.getElementById('progressStep');
        fill.style.width = '100%';
        percentEl.textContent = '100%';
        timeEl.textContent = '规划完成';
        stepEl.textContent = '';
        setTimeout(() => {
            submitBtn.disabled = false;
            document.getElementById('loadingOverlay').style.display = 'none';
        }, 500);
    }
});

function renderResult(data) {
    const content = document.getElementById('resultContent');
    const dayColors = [
        { bg: 'linear-gradient(135deg, #667eea, #764ba2)', color: '#667eea' },
        { bg: 'linear-gradient(135deg, #f093fb, #f5576c)', color: '#f093fb' },
        { bg: 'linear-gradient(135deg, #4facfe, #00f2fe)', color: '#4facfe' },
        { bg: 'linear-gradient(135deg, #43e97b, #38f9d7)', color: '#43e97b' },
        { bg: 'linear-gradient(135deg, #fa709a, #fee140)', color: '#fa709a' },
        { bg: 'linear-gradient(135deg, #a18cd1, #fbc2eb)', color: '#a18cd1' },
        { bg: 'linear-gradient(135deg, #ff9a9e, #fecfef)', color: '#ff9a9e' }
    ];
    
    let html = '';
    
    html += `
        <div class="weather-card">
            <h2>🌤️ ${data.city} 天气预报</h2>
            <div class="weather-grid">
                ${data.weather.map(w => `
                    <div class="weather-item">
                        <div class="weather-date">${w.date}</div>
                        <div class="weather-temp">${w.daytemp}°C / ${w.nighttemp}°C</div>
                        <div class="weather-desc">${w.dayweather}</div>
                    </div>
                `).join('')}
            </div>
        </div>
    `;
    
    if (data.travel_tips && data.travel_tips.length > 0) {
        html += `
            <div class="tips-section">
                <h2>💡 出行小贴士</h2>
                <ul class="tips-list">
                    ${data.travel_tips.map(tip => `<li>${tip}</li>`).join('')}
                </ul>
            </div>
        `;
    }
    
    data.daily_plans.forEach((day, idx) => {
        const colorIdx = idx % dayColors.length;
        const color = dayColors[colorIdx];
        
        html += `
            <div class="day-card">
                <div class="day-header">
                    <div class="day-badge" style="background: ${color.bg};">D${day.day}</div>
                    <div>
                        <div class="day-title">第${day.day}天行程</div>
                        <div class="day-date">${day.date} · ${day.weather.dayweather} ${day.weather.daytemp}°C</div>
                    </div>
                </div>
                
                <div class="spots-grid">
                    ${day.spots.map((spot, i) => `
                        <div class="spot-card">
                            ${spot.photo ? `<img src="${spot.photo}" style="width:100%;height:120px;object-fit:cover;border-radius:10px;margin-bottom:10px;" onerror="this.style.display='none'">` : ''}
                            <div class="spot-number" style="background: ${color.bg};">${i + 1}</div>
                            <div class="spot-name">${spot.name}</div>
                            <div class="spot-address">${spot.address || '暂无地址'}</div>
                            ${spot.intro ? `<div class="spot-intro">${spot.intro.length > 60 ? spot.intro.substring(0, 60) + '...' : spot.intro}</div>` : ''}
                            ${spot.detail_url ? `<a href="${spot.detail_url}" target="_blank" class="spot-detail-link">查看详情 ></a>` : ''}
                        </div>
                    `).join('')}
                </div>
                
                <div class="schedule-list">
                    ${day.schedule.map((item, i) => `
                        <div class="schedule-item">
                            <div class="schedule-time">${item.time}</div>
                            <div class="schedule-info">
                                <div class="schedule-name">${item.spot.name}</div>
                                <div class="schedule-detail">
                                    游览${item.visit_hours}小时 · 
                                    ${i === 0 ? '出发' : `打车${item.travel_time} · 约${item.taxi_cost}元`}
                                </div>
                            </div>
                        </div>
                    `).join('')}
                </div>
            </div>
        `;
    });
    
    if (data.food_recommendations && data.food_recommendations.length > 0) {
        html += `
            <div class="rec-section">
                <h2>🍜 美食推荐</h2>
                <div class="rec-grid">
                    ${data.food_recommendations.map(food => `
                        <div class="rec-item">
                            ${food.photo ? `<img src="${food.photo}" style="width:100%;height:150px;object-fit:cover;border-radius:10px;margin-bottom:10px;" onerror="this.style.display='none'">` : ''}
                            <div class="rec-name">${food.name}</div>
                            ${food.rating ? `<div class="rec-rating">⭐ ${food.rating}</div>` : ''}
                            <div class="rec-address">${food.address || '暂无地址'}</div>
                        </div>
                    `).join('')}
                </div>
            </div>
        `;
    }
    
    if (data.hotel_recommendations && data.hotel_recommendations.length > 0) {
        html += `
            <div class="rec-section">
                <h2>🏨 住宿推荐</h2>
                <div class="rec-grid">
                    ${data.hotel_recommendations.map(hotel => `
                        <div class="rec-item">
                            ${hotel.photo ? `<img src="${hotel.photo}" style="width:100%;height:150px;object-fit:cover;border-radius:10px;margin-bottom:10px;" onerror="this.style.display='none'">` : ''}
                            <div class="rec-name">${hotel.name}</div>
                            ${hotel.rating ? `<div class="rec-rating">⭐ ${hotel.rating}</div>` : ''}
                            <div class="rec-address">${hotel.address || '暂无地址'}</div>
                        </div>
                    `).join('')}
                </div>
            </div>
        `;
    }
    
    html += `
        <div class="map-section">
            <h2>🗺️ 路线地图</h2>
            <div class="map-tabs" id="mapTabs">
                ${data.daily_plans.map((day, idx) => {
                    const spots = day.spots_names || day.spots.map(s => s.name);
                    const routeText = spots.slice(0, 3).join(' → ');
                    return `<div class="map-tab ${idx === 0 ? 'active' : ''}" data-day="${idx}">第${day.day}天 ${routeText}</div>`;
                }).join('')}
            </div>
            <div class="map-description" id="mapDescription"></div>
            <div class="map-actions">
                <a href="#" target="_blank" class="map-btn" id="navLink">查看驾车导航</a>
                <a href="#" target="_blank" class="map-btn" id="taxiLink">一键打车</a>
            </div>
            <iframe id="mapIframe" class="map-iframe" src=""></iframe>
        </div>
    `;
    
    content.innerHTML = html;
    
    const mapData = data.daily_plans.map(day => ({
        url: day.map_url,
        spots: day.spots.map(s => s.name)
    }));
    
    function updateMap(dayIdx) {
        const mapInfo = mapData[dayIdx];
        if (mapInfo && mapInfo.url) {
            document.getElementById('mapIframe').src = mapInfo.url;
            document.getElementById('navLink').href = mapInfo.url;
            document.getElementById('taxiLink').href = mapInfo.url;
            document.getElementById('mapDescription').textContent = 
                `路线：${mapInfo.spots.join(' → ')}`;
        }
    }
    
    document.querySelectorAll('.map-tab').forEach(tab => {
        tab.addEventListener('click', function() {
            document.querySelectorAll('.map-tab').forEach(t => t.classList.remove('active'));
            this.classList.add('active');
            updateMap(parseInt(this.dataset.day));
        });
    });
    
    if (mapData.length > 0 && mapData[0].url) {
        updateMap(0);
    }
}
