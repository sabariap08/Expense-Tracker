# Expense Tracker Mobile (Flutter)

This is a native mobile app for the Expense Tracker backend. It uses the REST API added to the Flask server (`/api/*`).

## Features
- Login with session-based auth
- Dashboard with totals, monthly trend, category breakdown
- Transactions list with filters
- Add/Edit/Delete transactions
- Pull to refresh

## Setup
1. Start the Flask backend in `D:\Non Academics\Project\Expense Tracker` on `http://127.0.0.1:5000` or your server URL.
2. Open this folder in Flutter (Android Studio/VS Code).
3. Update `lib/config.dart` with your API base URL. Use `http://10.0.2.2:5000` for Android emulator, `http://127.0.0.1:5000` for iOS simulator/web/desktop.
4. Run `flutter pub get` and `flutter run`. You can test on Windows desktop, web, or Android emulator.

## API Endpoints Used
- POST /api/auth/login
- GET /api/auth/status
- POST /api/auth/logout
- GET /api/dashboard
- GET /api/transactions
- POST /api/transactions
- PUT /api/transactions/<id>
- DELETE /api/transactions/<id>
- GET /api/categories
