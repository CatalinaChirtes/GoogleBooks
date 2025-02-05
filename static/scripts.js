// const socket = io('https://booksapp-bjd0aqbra7bcbyh0.polandcentral-01.azurewebsites.net');
const socket = io('http://127.0.0.1:5000');

socket.on('message', function(data) {
    console.log(data);
});

socket.emit('available_genres');
socket.on('genre_results', function(data) {
    const genreSelect = document.getElementById('genreSelect');
    genreSelect.innerHTML = '<option value="">Select a genre</option>';
    
    data.genres.forEach(genre => {
        const option = document.createElement('option');
        option.value = genre;
        option.textContent = genre;
        genreSelect.appendChild(option);
    });
});

socket.on('book_results', function(data) {
    displayResults(data);
});

document.getElementById('query').addEventListener('keydown', function(event) {
    if (event.key === 'Enter') {
        sendQuery();
    }
});

function sendQuery() {
    const query = document.getElementById('query').value;

    if (!query) {
        if (!document.getElementById('notificationContainer').querySelector('.notification')) {
            displayNotification({ message: 'You must first search something before pressing Enter' });
        }
        return; 
    }

    socket.emit('book_query', { query: query });
}

function fetchNewReleases() {
    socket.emit('new_releases');
    document.getElementById('query').value = '';
    displayCategoryTitle("New Releases");
}

function fetchTopBooksByGenre() {
    const genre = document.getElementById('genreSelect').value;
    if (genre) {
        socket.emit('top_books_by_genre', { genre: genre });
        displayCategoryTitle(`Top Books in ${genre}`);
    } else {
        if (!document.getElementById('notificationContainer').querySelector('.notification')) {
            displayNotification({ message: 'Please select a genre' });
        }
    }
    document.getElementById('query').value = '';
}

function fetchBestsellers() {
    socket.emit('bestsellers');
    document.getElementById('query').value = '';
    displayCategoryTitle("Bestsellers");
}

function displayCategoryTitle(title) {
    const categoryTitleDiv = document.getElementById('categoryTitle');
    categoryTitleDiv.innerHTML = `<h2 class="category-heading text-2xl font-semibold text-white">${title}</h2>`;
}

function displayResults(data) {
    const resultsDiv = document.getElementById('results');
    resultsDiv.innerHTML = '';

    const maxBooks = 9;
    const booksToShow = data.books.slice(0, maxBooks);

    const gridContainer = document.createElement('div');
    gridContainer.className = 'book-grid-container';

    booksToShow.forEach(book => {
        const bookCard = document.createElement('div');
        bookCard.className = 'book-card';

        const imageUrl = book.thumbnail || '../static/images/placeholder_img.jpg';
        const genres = book.categories ? book.categories.join(', ') : 'Uncategorized';

        bookCard.innerHTML = `
            <div class="book-image">
                <img src="${imageUrl}" alt="${book.title}">
            </div>
            <div class="book-info">
                <div class="book-title">${book.title}</div>
                <div class="book-author">${book.authors.join(', ')}</div>
                <div class="book-genre">
                    <span class="genre-text">${genres}</span>
                </div>
            </div>
        `;
        gridContainer.appendChild(bookCard);

        bookCard.addEventListener('click', function() {
            openBookPopup(book);
        });
    });

    resultsDiv.appendChild(gridContainer);
}

function openBookPopup(book) {
    const popup = document.createElement('div');
    popup.className = 'book-popup';

    const imageUrl = book.thumbnail || '../static/images/placeholder_img.jpg';
    const genres = book.categories ? book.categories.join(', ') : 'Uncategorized';
    const description = book.description || 'No description available.';
    const rating = book.averageRating || 'No rating';
    const publishedDate = book.publishedDate || 'Unknown';

    popup.innerHTML = `
        <div class="popup-content">
            <div class="popup-header">
                <h2 class="popup-title">${book.title}</h2>
                <button class="popup-close-btn" onclick="closePopup()">X</button>
            </div>
            <div class="popup-body">
                <img src="${imageUrl}" alt="${book.title}" class="popup-image">
                <div class="popup-info">
                    <p><strong>Authors:</strong> ${book.authors.join(', ')}</p>
                    <p><strong>Genres:</strong> ${genres}</p>
                    <p><strong>Rating:</strong> ${rating}</p>
                    <p><strong>Published Date:</strong> ${publishedDate}</p>
                    <p><strong>Description:</strong><br> ${description}</p>
                    <a href="${book.infoLink}" target="_blank" class="popup-link">More Info</a>
                </div>
            </div>
        </div>
    `;

    document.body.appendChild(popup);
}

function closePopup() {
    const popup = document.querySelector('.book-popup');
    if (popup) {
        popup.remove();
    }
}

function displayNotification({ message }) {
    const notificationContainer = document.getElementById('notificationContainer');
    
    if (notificationContainer.querySelector('.notification')) {
        return;
    }

    const notification = document.createElement('div');
    notification.className = 'notification flex items-center p-4 rounded-lg text-white';
    notification.style.backgroundColor = '#71452e';
    notification.innerHTML = `<span>&#9888; ${message}</span>`;
    
    notificationContainer.appendChild(notification);

    setTimeout(() => {
        notification.remove();
    }, 5000);
}
