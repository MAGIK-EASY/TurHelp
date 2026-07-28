document.getElementById('search-btn').addEventListener('click', function() {
    document.body.style.overflow = 'auto';
    const citySelect = document.getElementById('select-city');
    const countrySelect = document.getElementById('select-country');

    const city = citySelect.value;
    const country = countrySelect.value;

    console.log('Selected city:', city);
    console.log('Selected country:', country);

    if (!city || !country) {
        alert('Пожалуйста, выберите город и страну');
        return;
    }

    fetch('/search_tours', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            city: city,
            country: country
        })
    })
    .then(response => response.json())
    .then(data => {
        const resultsContainer = document.querySelector('.tour-results');
        resultsContainer.innerHTML = '';

        if (data.agencies.length === 0) {
            resultsContainer.innerHTML = `
                <div class="alert alert-info">
                    По вашему запросу ничего не найдено
                </div>
            `;
			setTimeout(() => {
            resultsContainer.scrollIntoView(
			{
                behavior: 'smooth',
                block: 'start'
            }
			);
        }, 300);
            return;
        }

        // Создаем маппинг стран к изображениям
        const countryImages = {
            'Анапа': 'anapa.jpg',
            'Сочи': 'sochi.jpg',
            'Абхазия': 'abhazia.jpg',
            'Тайланд': 'thailand.jpg',
			'Египет': 'egypt.jpg',
			'Турция': 'turkish.jpg'
        };

        let resultsHTML = '';

        data.agencies.forEach((agency) => {
            const imageFile = countryImages[agency.country] || 'default.jpg';
			

            resultsHTML += `
            <div class="col-12 col-md-6 px-2 mb-3">
                <div class="tiles bg-body-tertiary h-100 overflow-hidden">
                    <div class="text-center position-relative"> 
                        <img src="static/images/${imageFile}" 
                            class="img-fluid w-100 clickable-tour" 
                            style="height: 200px; object-fit: cover; cursor: pointer;" 
                            alt="${agency.country}"
                            data-tour-id="${agency.id}"
                            data-name="${encodeURIComponent(agency.name)}"
                            data-address="${encodeURIComponent(agency.address)}"
                            data-country="${encodeURIComponent(agency.country)}"
                            data-price="${encodeURIComponent(agency.price)}"
                            data-description="${encodeURIComponent(agency.description || '')}"
                            data-duration="${encodeURIComponent(agency.duration || '')}"
                            data-image="${imageFile}">
                        <div class="position-absolute bottom-0 end-0 p-2 bg-dark bg-opacity-75 text-white rounded-start"> 
                            <i class="fas fa-star text-warning"></i>
                            <span class="ms-2 rating-value" data-tour-id="${agency.id}">Загрузка...</span>
                        </div>
                    </div>
                    <div class="p-3">
                        <h3 class="h1">${agency.name}</h3>
                        <p class="gl mb-1"><strong>Адрес:</strong> ${agency.address}</p>
                        <p class="gl mb-1"><strong>Страна:</strong> ${agency.country}</p>
                        <p class="gl mb-1"><strong>Средняя цена:</strong> ${agency.price} руб.</p>
                    </div>
                </div>
            </div>
            `;
        });

        resultsContainer.innerHTML = resultsHTML;

        // Загружаем рейтинги для всех карточек
        document.querySelectorAll('.rating-value').forEach(async (element) => {
            const tourId = element.getAttribute('data-tour-id');
            const rating = await getTourRating(tourId);
            element.textContent = rating.toFixed(1);
        });

        // Добавляем обработчики клика для всех изображений туров
		document.querySelectorAll('.clickable-tour').forEach(img => {
			img.addEventListener('click', function() {
				const tourData = {
					id: this.getAttribute('data-tour-id'),
					name: decodeURIComponent(this.getAttribute('data-name')),
					address: decodeURIComponent(this.getAttribute('data-address')),
					country: decodeURIComponent(this.getAttribute('data-country')),
					price: decodeURIComponent(this.getAttribute('data-price')),
					description: decodeURIComponent(this.getAttribute('data-description')),
					duration: decodeURIComponent(this.getAttribute('data-duration')),
					image: this.getAttribute('data-image')
				};
				
				// Сохраняем данные в sessionStorage
				sessionStorage.setItem('selectedTour', JSON.stringify(tourData));
				
				// Передаем только ID в URL
				window.location.href = `/Choosing_tour?tour_id=${tourData.id}`;
			});
		});

        // Прокрутка к результатам
        setTimeout(() => {
            resultsContainer.scrollIntoView(
			{
                behavior: 'smooth',
                block: 'start'
            }
			);
        }, 300);
    })
    .catch(error => {
        console.error('Error:', error);
        alert('Произошла ошибка при поиске');
    });
});

// Функция для получения рейтинга тура
async function getTourRating(tourId) {
    try {
        const response = await fetch(`/get_tour_rating/${tourId}`);
        const data = await response.json();
        if (data.success && data.reviews_count > 0) {
            return data.avg_rating;
        }
        return 0; // Возвращаем 0, если нет отзывов
    } catch (error) {
        console.error('Error fetching rating:', error);
        return 0;
    }
}