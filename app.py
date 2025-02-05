from flask import Flask, json, render_template, request
from flask_restx import Api, Resource, fields
from flask_cors import CORS
from flask_socketio import SocketIO, emit
import asyncio
import aiohttp
from dotenv import load_dotenv
import os

load_dotenv()

# API Keys
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
NYT_API_KEY = os.getenv('NYT_API_KEY')

app = Flask(__name__)
CORS(app)
api = Api(app, title="Books API", description="Search for books using Google Books API")

socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

book_model = api.model('BookSearch', {
    'query': fields.String(required=True, description='Search query for books')
})

ns = api.namespace('books', description='Book Search Operations')

client_counter = 0
clients = {}


def extract_book(item, fallback={}):
    volume_info = item.get('volumeInfo', fallback)
    return {
        'title': volume_info.get('title', fallback.get('title', 'Unknown Title')),
        'authors': volume_info.get('authors', fallback.get('authors', ['Unknown'])) or ['Unknown'],
        'description': volume_info.get('description', 'No description available.'),
        'categories': volume_info.get('categories', ['Uncategorized']),
        'averageRating': volume_info.get('averageRating', 'No rating'),
        'publishedDate': volume_info.get('publishedDate', 'Unknown'),
        'thumbnail': volume_info.get('imageLinks', {}).get('thumbnail'),
        'infoLink': volume_info.get('infoLink')
    }


# ========== Async Fetching Functions ==========

async def fetch_books(url):
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url) as response:
                response.raise_for_status()
                books_data = await response.json()
                return [extract_book(item) for item in books_data.get('items', [])]
        except aiohttp.ClientError as e:
            return {"error": str(e)}


async def fetch_bestsellers():
    nyt_url = f"https://api.nytimes.com/svc/books/v3/lists/current/hardcover-fiction.json?api-key={NYT_API_KEY}"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(nyt_url) as nyt_response:
                nyt_response.raise_for_status()
                nyt_data = await nyt_response.json()
                tasks = []

                for book in nyt_data['results']['books']:
                    isbn = book['isbns'][0].get('isbn13') if book.get('isbns') else None
                    if isbn:
                        google_url = f"https://www.googleapis.com/books/v1/volumes?q=isbn:{isbn}&key={GOOGLE_API_KEY}"
                        tasks.append(fetch_books(google_url))

                books_info = await asyncio.gather(*tasks)
                return [book for sublist in books_info for book in sublist]

    except aiohttp.ClientError as e:
        return {"error": str(e)}


# ========== Flask REST API Endpoint ==========

@app.route('/book')
def home():
    return render_template('book.html')


@ns.route('/search')
class BookSearch(Resource):
    @ns.expect(book_model)
    def post(self):
        data = request.get_json()
        query = data['query']
        url = f"https://www.googleapis.com/books/v1/volumes?q={query}&key={GOOGLE_API_KEY}"
        books_info = asyncio.run(fetch_books(url))
        return json.dumps(books_info)


@ns.route('/genres')
class AvailableGenres(Resource):
    def get(self):
        subjects = ['fiction', 'non-fiction', 'mystery', 'romance', 'science']
        genres = set()

        for subject in subjects:
            url = f"https://www.googleapis.com/books/v1/volumes?q=subject:{subject}&key={GOOGLE_API_KEY}"
            books_info = asyncio.run(fetch_books(url))
            if isinstance(books_info, list):
                for book in books_info:
                    genres.update(book.get('categories', []))
            else:
                return json.dumps(books_info), 500

        return json.dumps({'genres': sorted(genres)})


# ========== SocketIO Handlers ==========

@socketio.on('connect')
def handle_connect():
    global client_counter
    client_counter += 1
    clients[request.sid] = client_counter
    print(f'Client {client_counter} connected')
    emit('message', {'data': f'Connected to the server as Client {client_counter}'})


@socketio.on('disconnect')
def handle_disconnect():
    global client_counter
    client_id = clients.pop(request.sid, None)
    if client_id:
        print(f'Client {client_id} disconnected')

    if not clients:
        client_counter = 0


@socketio.on('book_query')
def handle_book_query(data):
    query = data['query']
    url = f"https://www.googleapis.com/books/v1/volumes?q={query}&key={GOOGLE_API_KEY}"
    books_info = asyncio.run(fetch_books(url))
    emit('book_results', {'books': books_info})


@socketio.on('new_releases')
def handle_new_releases():
    url = f"https://www.googleapis.com/books/v1/volumes?q=just+uploaded&orderBy=newest&key={GOOGLE_API_KEY}"
    books_info = asyncio.run(fetch_books(url))
    emit('book_results', {'books': books_info})


@socketio.on('top_books_by_genre')
def handle_books_by_genre(data):
    genre = data['genre']
    url = f"https://www.googleapis.com/books/v1/volumes?q=subject:{genre}&key={GOOGLE_API_KEY}"
    books_info = asyncio.run(fetch_books(url))
    emit('book_results', {'books': books_info})


@socketio.on('bestsellers')
def handle_bestsellers():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    books_info = asyncio.run(fetch_bestsellers())
    emit('book_results', {'books': books_info})


@socketio.on('available_genres')
def handle_available_genres():
    genres = [
        "Adventure and adventurers", "Architecture", "Armies", "Art", 
        "Art museum curators", "Biography", "Biography & Autobiography", 
        "Business & Economics", "Classic fiction", "Computers", "Ego (Psychology)", 
        "England", "Fiction", "History", "Juvenile Fiction", "Language Arts & Disciplines", 
        "Literary Criticism", "Man-woman relationships", "Mathematics", "Medical", 
        "Philosophy", "Political Science", "Psychology", "Science", "Self-Help"
    ]
    
    emit('genre_results', {'genres': sorted(genres)})


api.add_namespace(ns, path='/api')

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    socketio.run(app, host='0.0.0.0', port=port, debug=True)
