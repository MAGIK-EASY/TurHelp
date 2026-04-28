// Функция для отображения звезд рейтинга
function displayRating(rating) {
	const starsContainer = document.getElementById('stars-display');
	const fullStars = Math.floor(rating);
	const hasHalfStar = rating % 1 >= 0.5;

	starsContainer.innerHTML = '';

	// Добавляем полные звезды
	for (let i = 0; i < fullStars; i++) {
		starsContainer.innerHTML += '<i class="fas fa-star text-warning"></i>';
	}

	// Добавляем половину звезды если нужно
	if (hasHalfStar) {
		starsContainer.innerHTML += '<i class="fas fa-star-half-alt text-warning"></i>';
	}

	// Добавляем пустые звезды
	const emptyStars = 5 - fullStars - (hasHalfStar ? 1 : 0);
	for (let i = 0; i < emptyStars; i++) {
		starsContainer.innerHTML += '<i class="far fa-star text-warning"></i>';
	}
}

// Функция загрузки рейтинга тура
function loadTourRating(tourId) {
	fetch(`/get_tour_rating/${tourId}`)
		.then(response => {
			if (!response.ok) throw new Error('Ошибка загрузки рейтинга');
			return response.json();
		})
		.then(data => {
			if (data.success) {
				const ratingText = document.getElementById('rating-text');

				if (data.reviews_count > 0) {
					displayRating(data.avg_rating);
					ratingText.textContent = `${data.avg_rating} (${data.reviews_count} отзывов)`;
				} else {
					displayRating(0);
					ratingText.textContent = "Нет отзывов";
				}
			} else {
				throw new Error(data.error || 'Неизвестная ошибка');
			}
		})
		.catch(error => {
			console.error('Error loading rating:', error);
			document.getElementById('rating-text').textContent = "Ошибка загрузки рейтинга";
		});
}

document.addEventListener('DOMContentLoaded', function() {
	// Получаем данные тура из sessionStorage
	const tourData = JSON.parse(sessionStorage.getItem('selectedTour'));
	
	// Получаем ID тура из URL или из sessionStorage
	const urlParams = new URLSearchParams(window.location.search);
	let tourId = urlParams.get('tour_id');
	
	// Если нет данных в sessionStorage, используем ID из URL
	if (!tourData) {
		if (!tourId) {
			console.error('Нет данных о туре');
			return;
		}
		// Если есть только ID, можно загрузить данные с сервера
		fetchTourDataFromServer(tourId);
		return;
	}
	
	// Используем ID из данных тура, если он не передан в URL
	if (!tourId) {
		tourId = tourData.id;
	}
	
	// Загружаем рейтинг тура
	loadTourRating(tourId);
	
	// Устанавливаем изображение тура
	const imageFile = tourData.image || 'default.jpg';
	document.getElementById('tour-image').src = `static/images/${imageFile}`;
	
	// Обновляем информацию о туре из sessionStorage
	document.getElementById('tour-name').textContent = tourData.name || 'Название тура';
	document.getElementById('tour-address').textContent = tourData.address || 'Адрес не указан';
	document.getElementById('tour-country').textContent = tourData.country || 'Страна не указана';
	document.getElementById('tour-price').textContent = (tourData.price || 'Цена не указана') + ' руб.';
	document.getElementById('tour-description').textContent = tourData.description || 'Описание отсутствует';
	
	// Устанавливаем длительность, если есть такой элемент
	const durationElement = document.getElementById('tour-duration');
	if (durationElement && tourData.duration) {
		durationElement.textContent = tourData.duration;
	}

	// Функция загрузки отзывов
	function loadReviews() {
    fetch(`/get_reviews/${tourId}`)
        .then(response => {
            if (!response.ok) throw new Error('Ошибка загрузки отзывов');
            return response.json();
        })
        .then(data => {
            const container = document.getElementById('reviews-container');
            container.innerHTML = '';

            // После загрузки отзывов обновляем рейтинг
            loadTourRating(tourId);

            if (!data.reviews || data.reviews.length === 0) {
                container.innerHTML = '<div class="alert alert-info">Пока нет отзывов. Будьте первым!</div>';
                return;
            }

            data.reviews.forEach(review => {
                const stars = '★'.repeat(review.stars) + '☆'.repeat(5 - review.stars);
                const reviewElement = document.createElement('div');
                reviewElement.className = 'card mb-3';
                reviewElement.id = `review-${review.id}`;

                // Проверяем по ID, имя не нужно
                const canDelete = (currentUserId && currentUserId.toString() === review.client_id.toString()) || isAdmin;

                reviewElement.innerHTML = `
                    <div class="card-body">
                        <div class="d-flex justify-content-between align-items-start">
                            <div class="d-flex align-items-center gap-3">
                                <img src="${review.avatar}" 
                                     alt="${review.full_name}" 
                                     class="rounded-circle"
                                     style="width: 50px; height: 50px; object-fit: cover;"
                                     onerror="this.src='/static/images/default-avatar.png'">
                                <div>
                                    <h6 class="card-title mb-1">${review.full_name}</h6>
                                    <div class="mb-1 text-warning">${stars}</div>
                                </div>
                            </div>
                            ${canDelete ? `
                                <button class="btn btn-sm btn-outline-danger delete-review" data-review-id="${review.id}">
                                    <i class="fas fa-trash"></i>
                                </button>
                            ` : ''}
                        </div>
                        <p class="card-text mt-3">${escapeHtml(review.description)}</p>
                        <small class="text-muted">
                            <i class="far fa-calendar-alt me-1"></i>${new Date(review.date).toLocaleDateString('ru-RU')}
                        </small>
                    </div>
                `;
                container.appendChild(reviewElement);
            });
        })
        .catch(error => {
            console.error('Error:', error);
            document.getElementById('reviews-container').innerHTML =
                `<div class="alert alert-danger">Ошибка загрузки отзывов: ${error.message}</div>`;
        });
}

	// Обработчик отправки нового отзыва
	const submitBtn = document.getElementById('submit-review');
	if (submitBtn) {
		submitBtn.addEventListener('click', function() {
			const stars = document.getElementById('review-stars').value;
			const text = document.getElementById('review-text').value.trim();

			if (!text) {
				alert('Пожалуйста, введите текст отзыва');
				return;
			}

			fetch('/add_review', {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
				},
				body: JSON.stringify({
					tour_id: tourId,
					stars: stars,
					description: text
				})
			})
				.then(response => {
					if (!response.ok) {
						return response.json().then(err => { throw new Error(err.error || 'Ошибка сервера'); });
					}
					return response.json();
				})
				.then(data => {
					if (data.success) {
						document.getElementById('review-text').value = '';
						loadReviews();
					} else {
						throw new Error(data.error || 'Неизвестная ошибка');
					}
				})
				.catch(error => {
					console.error('Error:', error);
					alert('Ошибка при отправке отзыва: ' + error.message);
				});
		});
	}

	// Обработчик удаления отзывов
	document.addEventListener('click', function(e) {
		if (e.target.classList.contains('delete-review') ||
			e.target.closest('.delete-review')) {
			const button = e.target.classList.contains('delete-review') ?
				e.target : e.target.closest('.delete-review');
			const reviewId = button.dataset.reviewId;

			if (confirm('Вы уверены, что хотите удалить этот отзыв?')) {
				fetch(`/delete_review/${reviewId}`, {
					method: 'DELETE',
					headers: {
						'Content-Type': 'application/json',
					}
				})
					.then(response => {
						if (!response.ok) {
							return response.json().then(err => { throw new Error(err.error || 'Ошибка сервера'); });
						}
						return response.json();
					})
					.then(data => {
						if (data.success) {
							document.getElementById(`review-${reviewId}`).remove();
							if (document.getElementById('reviews-container').children.length === 0) {
								document.getElementById('reviews-container').innerHTML =
									'<div class="alert alert-info">Пока нет отзывов. Будьте первым!</div>';
							}
						} else {
							throw new Error(data.error || 'Неизвестная ошибка');
						}
					})
					.catch(error => {
						console.error('Error:', error);
						alert('Ошибка при удалении отзыва: ' + error.message);
					});
			}
		}
	});

	// Первоначальная загрузка отзывов
	loadReviews();
});

// Резервная функция для загрузки данных с сервера (если нет данных в sessionStorage)
function fetchTourDataFromServer(tourId) {
	fetch(`/get_tour_details/${tourId}`)
		.then(response => {
			if (!response.ok) throw new Error('Ошибка загрузки данных тура');
			return response.json();
		})
		.then(tourData => {
			// Загружаем рейтинг тура
			loadTourRating(tourId);
			
			// Устанавливаем изображение тура
			const imageFile = tourData.image || 'default.jpg';
			document.getElementById('tour-image').src = `static/images/${imageFile}`;
			
			// Обновляем информацию о туре
			document.getElementById('tour-name').textContent = tourData.name || 'Название тура';
			document.getElementById('tour-address').textContent = tourData.address || 'Адрес не указан';
			document.getElementById('tour-country').textContent = tourData.country || 'Страна не указана';
			document.getElementById('tour-price').textContent = (tourData.price || 'Цена не указана') + ' руб.';
			document.getElementById('tour-description').textContent = tourData.description || 'Описание отсутствует';
			
			const durationElement = document.getElementById('tour-duration');
			if (durationElement && tourData.duration) {
				durationElement.textContent = tourData.duration;
			}
			
			// Загружаем отзывы
			loadReviews();
		})
		.catch(error => {
			console.error('Error loading tour data:', error);
			alert('Ошибка при загрузке данных тура');
		});
}

// Вспомогательная функция для экранирования HTML
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}