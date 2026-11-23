# School POS Backend Setup

## Quick Install (Windows)

1. **Install PostgreSQL**
   - Download from: https://www.enterprisedb.com/downloads/postgres-postgresql-downloads
   - During install, set password: `postgres`
   - Make sure port is: `5432`

2. **Install Python**
   - Download Python 3.9+ from: https://www.python.org/downloads/
   - IMPORTANT: Check "Add Python to PATH"

3. **Run Installer**
   ```
   Double-click: install.bat
   ```

4. **Start Server**
   ```
   Double-click: start.bat
   ```

## For Auto-Start on Boot

Run: `add_startup.bat`

## Troubleshooting

### PostgreSQL not found
Make sure PostgreSQL is installed and in PATH

### Database connection error
Check that PostgreSQL is running and credentials are correct

### Port 8000 in use
Change port in start.bat or kill the process using port 8000

## Connect Client App
The client should connect to:
```
http://YOUR_SERVER_IP:8000
```

## Default Admin Login
After creating superuser, login at:
```
http://YOUR_SERVER_IP:8000/admin/
```
