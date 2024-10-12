## SessionSpyre

SessionSpyre is a comprehensive web application designed to track and replay user sessions on a website. It provides detailed insights into user interactions, helping developers and analysts understand user behavior and improve the user experience. The project leverages modern web technologies and frameworks to deliver a robust and scalable solution.

### Features

- **User Session Recording**: Capture and replay user sessions to analyze user behavior and interactions.
- **Real-time Monitoring**: Monitor user activities in real-time with WebSocket connections.
- **User Authentication**: Secure user authentication and session management.
- **Admin Interface**: Manage users, sites, and session data through a user-friendly admin interface.
- **Customizable Exclusions**: Define URL exclusion rules to filter out irrelevant data.
- **Responsive Design**: Fully responsive design using Tailwind CSS for a seamless experience across devices.

### Technologies Used

- **Backend**: Django, Django REST Framework
- **Frontend**: JavaScript, rrweb, Tailwind CSS, Alpine.js, HTMX
- **Database**: PostgreSQL
- **WebSockets**: Django Channels
- **Deployment**: Docker, Nginx

### Project Structure

- `session_tracker/static/js/record.js`: Handles the recording of user sessions and WebSocket connections.
- `SessionSpyre/urls.py`: Defines the URL routing for the Django application.
- `templates/base.html`: Base HTML template for the application, including CSS and JavaScript imports.

### Installation

1. **Clone the repository**:
    ```sh
    git clone https://github.com/JimGalvan/SessionSpyre.git
    cd SessionSpyre
    ```

2. **Set up the virtual environment**:
    ```sh
    python -m venv venv
    source venv/bin/activate  # On Windows use `venv\Scripts\activate`
    ```

3. **Install dependencies**:
    ```sh
    pip install -r requirements.txt
    ```

4. **Apply migrations**:
    ```sh
    python manage.py migrate
    ```

5. **Run the development server**:
    ```sh
    python manage.py runserver
    ```

### Usage

1. **Access the application**: Open your browser and navigate to `http://127.0.0.1:8000/`.
2. **Admin Interface**: Access the admin interface at `http://127.0.0.1:8000/admin/` to manage users and session data.
3. **Session Recording**: Integrate the session recording script into your website to start capturing user sessions.
