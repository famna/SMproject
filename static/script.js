/**
 * Клієнтський JavaScript для роботи з API
 */

// Елементи DOM
const loadBtn = document.getElementById('loadBtn');
const searchInput = document.getElementById('searchInput');
const sortSelect = document.getElementById('sortSelect');
const filterAwards = document.getElementById('filterAwards');
const rangeInputs = document.getElementById('rangeInputs');
const minAwardsInput = document.getElementById('minAwards');
const maxAwardsInput = document.getElementById('maxAwards');

const cardsContainer = document.getElementById('cardsContainer');
const loadingDiv = document.getElementById('loading');
const errorDiv = document.getElementById('error');
const statsDiv = document.getElementById('stats');

// ЕЛЕМЕНТИ ДЛЯ ПАГІНАЦІЇ
const paginationControls = document.getElementById('paginationControls');
const showMoreBtn = document.getElementById('showMoreBtn');

// Глобальні змінні
let debounceTimer;
let currentArtistsList = []; // Зберігаємо весь відфільтрований список тут
let visibleCount = 0;        // Скільки зараз показано
const ITEMS_PER_PAGE = 8;    // Скільки показувати за раз

// Функція для завантаження даних з API
async function loadData() {
    try {
        loadBtn.disabled = true;
        loadingDiv.style.display = 'block';
        errorDiv.style.display = 'none';
        cardsContainer.innerHTML = '';
        paginationControls.style.display = 'none'; // Ховаємо кнопку при завантаженні

        const response = await fetch('/api/artists');
        const result = await response.json();

        if (!result.success) throw new Error(result.error);

        updateStats(result.stats);
        renderCards(result.data); // Тут викликається наша оновлена функція
        statsDiv.style.display = 'flex';
        
    } catch (error) {
        showError(`Помилка: ${error.message}`);
    } finally {
        loadingDiv.style.display = 'none';
        loadBtn.disabled = false;
    }
}
//ФУНКЦІЯ ПОШУКУ І ФІЛЬТРАЦІЇ
async function searchAndFilter() {
    try {
        loadingDiv.style.display = 'block';
        paginationControls.style.display = 'none'; // Ховаємо кнопку
        
        const params = new URLSearchParams({
            q: searchInput.value,
            sort: sortSelect.value,
            filter: filterAwards.value,
            min: minAwardsInput.value || 0,
            max: maxAwardsInput.value || ''
        });

        const response = await fetch(`/api/artists/search?${params}`);
        const result = await response.json();

        if (!result.success) throw new Error(result.error);

        updateStats(result.stats);
        renderCards(result.data); // Оновлена функція
        
    } catch (error) {
        showError(`Помилка: ${error.message}`);
    } finally {
        loadingDiv.style.display = 'none';
    }
}

// === ОНОВЛЕНА ЛОГІКА РЕНДЕРИНГУ ===

function renderCards(artists) {
    // 1. Очищаємо контейнер
    cardsContainer.innerHTML = '';
    
    // 2. Зберігаємо новий список у глобальну змінну
    currentArtistsList = artists;
    
    // 3. Скидаємо лічильник
    visibleCount = 0;

    // 4. Перевіряємо, чи є дані
    if (artists.length === 0) {
        cardsContainer.innerHTML = `
            <div class="no-data">
                <div class="no-data-icon">🎤</div>
                <h2>Немає результатів</h2>
                <p>Спробуйте змінити параметри пошуку</p>
            </div>
        `;
        paginationControls.style.display = 'none';
        return;
    }

    // 5. Показуємо першу порцію
    showMoreItems();
}

function showMoreItems() {
    // Визначаємо, скільки карток додати
    const nextBatch = currentArtistsList.slice(visibleCount, visibleCount + ITEMS_PER_PAGE);
    
    // Додаємо їх в DOM
    nextBatch.forEach(artist => {
        const card = createCard(artist);
        // Додаємо анімацію появи
        card.style.animation = `fadeIn 0.5s ease forwards`; 
        cardsContainer.appendChild(card);
    });

    // Оновлюємо лічильник
    visibleCount += nextBatch.length;

    // Оновлюємо текст на кнопці (опціонально)
    const remaining = currentArtistsList.length - visibleCount;
    showMoreBtn.innerHTML = remaining > 0 
        ? `⬇️ Показати ще (${remaining} залишилось)` 
        : `Більше немає`;

    // Показуємо або ховаємо кнопку
    if (visibleCount >= currentArtistsList.length) {
        paginationControls.style.display = 'none';
    } else {
        paginationControls.style.display = 'flex';
    }
}
// Функція для створення HTML-картки виконавця
function createCard(artist) {

    const card = document.createElement('div');
    card.className = 'card';
    

    const birthDateHtml = artist.birth_date_formatted 
        ? `<div class="info-row"><span class="info-icon">📅</span><div><span class="info-label">Дата народження:</span><span class="info-value">${artist.birth_date_formatted}</span></div></div>` 
        : '';
    const birthPlaceHtml = artist.birth_place
        ? `<div class="info-row"><span class="info-icon">📍</span><div><span class="info-label">Місце народження:</span><span class="info-value">${artist.birth_place}</span></div></div>`
        : '';
    const awardsHtml = artist.awards_count > 0
        ? `<div class="awards-badge"><span class="icon">🏆</span><span>${artist.awards_count} ${getNagrodWord(artist.awards_count)}</span></div>`
        : '<div class="info-row"><span class="info-icon">ℹ</span><span class="info-value">Без нагород у базі</span></div>';

    card.innerHTML = `
        <div class="card-header"><h2 class="artist-name">${escapeHtml(artist.name)}</h2></div>
        <div class="card-body">${birthDateHtml}${birthPlaceHtml}${awardsHtml}</div>
    `;
    return card;
}
// === Event Listeners ===
loadBtn.addEventListener('click', loadData);
searchInput.addEventListener('input', debounce(() => { searchAndFilter(); }, 500));
sortSelect.addEventListener('change', searchAndFilter);
// Слухач для фільтра нагород

filterAwards.addEventListener('change', () => {
    if (filterAwards.value === 'custom') {
        rangeInputs.style.display = 'flex';
    } else {
        rangeInputs.style.display = 'none';
        minAwardsInput.value = '';
        maxAwardsInput.value = '';
    }
    searchAndFilter();
});

// Слухачі для полів діапазону
minAwardsInput.addEventListener('input', debounce(() => { searchAndFilter(); }, 500));
maxAwardsInput.addEventListener('input', debounce(() => { searchAndFilter(); }, 500));

// НОВИЙ СЛУХАЧ ДЛЯ КНОПКИ
showMoreBtn.addEventListener('click', showMoreItems);

window.addEventListener('load', () => {
    loadData();
});

// Допоміжні функції
function debounce(func, delay) {
    return function() {
        clearTimeout(debounceTimer);
        debounceTimer = setTimeout(() => func.apply(this, arguments), delay);
    };
}
// Функція для оновлення статистики
function updateStats(stats) {
    document.getElementById('totalAwardsDisplay').textContent = stats.total_awards;
    document.getElementById('totalArtistsDisplay').textContent = stats.total_artists;
    document.getElementById('avgAwards').textContent = stats.avg_awards;
}
// Функція для відображення помилок
function showError(message) {
    errorDiv.innerHTML = `<strong>❌ Помилка!</strong><br>${escapeHtml(message)}`;
    errorDiv.style.display = 'block';
}
// Функція для безпечного виведення тексту (захист від XSS)
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}
// Функція для отримання правильного слова "нагорода" в залежності від кількості
function getNagrodWord(count) { 
    const lastDigit = count % 10;
    const lastTwoDigits = count % 100;
    if (lastTwoDigits >= 11 && lastTwoDigits <= 14) return 'нагород';
    if (lastDigit === 1) return 'нагорода';
    if (lastDigit >= 2 && lastDigit <= 4) return 'нагороди';
    return 'нагород';
}