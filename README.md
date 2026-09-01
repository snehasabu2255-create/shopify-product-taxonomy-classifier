# Shopify Django App

A robust, scalable Django-based application designed to integrate with Shopify.

## Features

* Seamless Shopify integration
* Secure authentication and authorization
* Efficient data management and synchronization
* Intuitive user interface

## Tech Stack

* **Backend:** Python, Django
* **Database:** MariaDB
* **Frontend:** HTML, CSS, JavaScript

## Local Setup & Installation

Follow these instructions to set up the project locally.

### Prerequisites

Ensure you have the following installed on your system:
* Python 3.x
* MariaDB

### 1. Set Up Virtual Environment

Create and activate a virtual environment to manage project dependencies:

**Windows:**
```bash
python -m venv venv
venv\Scripts\activate
```

**macOS/Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

### 2. Install Dependencies

Install the required Python packages using pip:

```bash
pip install -r requirements.txt
```

### 3. Configure Environment Variables

Create a `.env` file in the project root directory and add the necessary environment variables. 

Example `.env` configuration:
```env
SECRET_KEY=your_secret_key_here
DEBUG=True
DB_NAME=your_db_name
DB_USER=your_db_user
DB_PASSWORD=your_db_password
DB_HOST=localhost
DB_PORT=3306
```

### 4. Database Setup & Configuration

Ensure your MariaDB service is running. This project is configured to use **MariaDB** for data storage. Create a database that matches the `DB_NAME` specified in your `.env` file.

Start the MariaDB service (the command varies by operating system).

### 5. Run Migrations

Apply Django migrations to set up your database schema:

```bash
python manage.py migrate
```

### 6. Start the Development Server

Run the Django development server:

```bash
python manage.py runserver
```

The application will be accessible at `http://localhost:8000/`.
