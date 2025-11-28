/**
 * Клієнтський JavaScript для роботи з API
 */

// Елементи DOM
const loadBtn = document.getElementById('loadBtn');
const searchInput = document.getElementById('searchInput');
const sortSelect = document.getElementById('sortSelect');
// const filterAwards видалено
const cardsContainer = document.getElementById('cardsContainer');
const loadingDiv = document.getElementById('loading');
const errorDiv = document.getElementById('error');
const statsDiv = document.getElementById('stats');

// Глобальні змінні
let debounceTimer;

/**
 * Завантаження даних про виконавців
 */
async function loadData() {
    try {
        loadBtn.disabled = true;
        loadingDiv.style.display = 'block';
        errorDiv.style.display = 'none';
        cardsContainer.innerHTML = '';

        const response = await fetch('/api/artists');
        const result = await response.json();

        if (!result.success) {
            throw new Error(result.error);
        }

        updateStats(result.stats);
        renderCards(result.data);
        statsDiv.style.display = 'flex';
        
    } catch (error) {
        showError(`Помилка завантаження даних: ${error.message}`);
        console.error('Error:', error);
    } finally {
        loadingDiv.style.display = 'none';
        loadBtn.disabled = false;
    }
}

/**
 * Пошук виконавців
 */
async function searchAndFilter() {
    try {
        loadingDiv.style.display = 'block';
        errorDiv.style.display = 'none';

        const params = new URLSearchParams({
            q: searchInput.value,
            sort: sortSelect.value
            // filter видалено
        });

        const response = await fetch(`/api/artists/search?${params}`);
        const result = await response.json();

        if (!result.success) {
            throw new Error(result.error);
        }

        updateStats(result.stats);
        renderCards(result.data);
        
    } catch (error) {
        showError(`Помилка пошуку: ${error.message}`);
        console.error('Error:', error);
    } finally {
        loadingDiv.style.display = 'none';
    }
}

/**
 * Відображення карток виконавців
 */
function renderCards(artists) {
    cardsContainer.innerHTML = '';

    if (artists.length === 0) {
        cardsContainer.innerHTML = `
            <div class="no-data">
                <div class="no-data-icon">🎤</div>
                <h2>Немає результатів</h2>
                <p>Спробуйте змінити параметри пошуку</p>
            </div>
        `;
        return;
    }

    artists.forEach(artist => {
        const card = createCard(artist);
        cardsContainer.appendChild(card);
    });
}

/**
 * Створення HTML картки виконавця
 */
function createCard(artist) {
    const card = document.createElement('div');
    card.className = 'card';

    const birthDateHtml = artist.birth_date_formatted 
        ? `
            <div class="info-row">
                <span class="info-icon">📅</span>
                <div>
                    <span class="info-label">Дата народження:</span>
                    <span class="info-value">${artist.birth_date_formatted}</span>
                </div>
            </div>
        `
        : '';

    const birthPlaceHtml = artist.birth_place
        ? `
            <div class="info-row">
                <span class="info-icon">📍</span>
                <div>
                    <span class="info-label">Місце народження:</span>
                    <span class="info-value">${artist.birth_place}</span>
                </div>
            </div>
        `
        : '';

    const awardsHtml = artist.awards_count > 0
        ? `
            <div class="awards-badge">
                <span class="icon">🏆</span>
                <span>${artist.awards_count} ${getNagrodWord(artist.awards_count)}</span>
            </div>
        `
        : '<div class="info-row"><span class="info-icon">ℹ️</span><span class="info-value">Без нагород у базі</span></div>';

    card.innerHTML = `
        <div class="card-header">
            <h2 class="artist-name">${escapeHtml(artist.name)}</h2>
        </div>
        <div class="card-body">
            ${birthDateHtml}
            ${birthPlaceHtml}
            ${awardsHtml}
        </div>
    `;

    return card;
}

/**
 * Правильне відмінювання слова "нагорода"
 */
function getNagrodWord(count) {
    const lastDigit = count % 10;
    const lastTwoDigits = count % 100;

    if (lastTwoDigits >= 11 && lastTwoDigits <= 14) {
        return 'нагород';
    }
    if (lastDigit === 1) {
        return 'нагорода';
    }
    if (lastDigit >= 2 && lastDigit <= 4) {
        return 'нагороди';
    }
    return 'нагород';
}

/**
 * Оновлення статистики
 */
function updateStats(stats) {
    // Оновлена логіка відображення
    document.getElementById('totalAwardsDisplay').textContent = stats.total_awards;
    document.getElementById('totalArtistsDisplay').textContent = stats.total_artists;
    document.getElementById('avgAwards').textContent = stats.avg_awards;
}

/**
 * Відображення повідомлення про помилку
 */
function showError(message) {
    errorDiv.innerHTML = `
        <strong>❌ Помилка!</strong><br>
        ${escapeHtml(message)}
    `;
    errorDiv.style.display = 'block';
}

/**
 * Екранування HTML
 */
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

/**
 * Debounce
 */
function debounce(func, delay) {
    return function() {
        clearTimeout(debounceTimer);
        debounceTimer = setTimeout(() => func.apply(this, arguments), delay);
    };
}

// Event listeners
loadBtn.addEventListener('click', loadData);

searchInput.addEventListener('input', debounce(() => {
    searchAndFilter();
}, 500));

sortSelect.addEventListener('change', searchAndFilter);
// filterAwards listener видалено

// Автоматичне завантаження
window.addEventListener('load', () => {
    loadData();
});