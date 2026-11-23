import 'dart:convert';

import 'package:flutter/foundation.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:http/http.dart' as http;

class AuthProvider extends ChangeNotifier {
  static const _storage = FlutterSecureStorage();
  static const _baseUrl = 'http://10.0.2.2:8000/api';

  String? _accessToken;
  String? _refreshToken;
  Map<String, dynamic>? _currentUser;
  bool _isLoading = false;
  String? _errorMessage;

  String? get accessToken => _accessToken;
  String? get refreshToken => _refreshToken;
  Map<String, dynamic>? get currentUser => _currentUser;
  bool get isLoading => _isLoading;
  String? get errorMessage => _errorMessage;
  bool get isLoggedIn => _accessToken != null;

  String get userName =>
      _currentUser?['name'] as String? ?? 'User';
  String get userPhone =>
      _currentUser?['phone_number'] as String? ?? '';
  String get userRole =>
      _currentUser?['role'] as String? ?? 'buyer';
  bool get isSeller => userRole == 'seller';
  bool get isMiddleman => userRole == 'middleman';
  bool get isAdmin => userRole == 'administrator';

  Future<void> _saveTokens(String access, String refresh) async {
    await _storage.write(key: 'access_token', value: access);
    await _storage.write(key: 'refresh_token', value: refresh);
    _accessToken = access;
    _refreshToken = refresh;
    notifyListeners();
  }

  Future<Map<String, String>> _authHeaders() async {
    return {
      'Content-Type': 'application/json',
      if (_accessToken != null) 'Authorization': 'Bearer $_accessToken',
    };
  }

  Future<void> loadTokens() async {
    _accessToken = await _storage.read(key: 'access_token');
    _refreshToken = await _storage.read(key: 'refresh_token');
    notifyListeners();
  }

  Future<void> login({
    required String phoneNumber,
    required String password,
  }) async {
    _isLoading = true;
    _errorMessage = null;
    notifyListeners();

    try {
      final response = await http
          .post(
            Uri.parse('$_baseUrl/token/'),
            headers: {'Content-Type': 'application/json'},
            body: jsonEncode({
              'phone_number': phoneNumber,
              'password': password,
            }),
          )
          .timeout(const Duration(seconds: 15));

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body) as Map<String, dynamic>;
        await _saveTokens(
          data['access'] as String,
          data['refresh'] as String,
        );
        await fetchCurrentUser();
      } else {
        final data = jsonDecode(response.body) as Map<String, dynamic>;
        _errorMessage = data['detail'] as String? ?? 'Login failed';
      }
    } catch (e) {
      _errorMessage = 'Network error: $e';
    }

    _isLoading = false;
    notifyListeners();
  }

  Future<void> loginWithOtp(String phoneNumber, String otp) async {
    _isLoading = true;
    _errorMessage = null;
    notifyListeners();

    try {
      final response = await http
          .post(
            Uri.parse('$_baseUrl/verify-otp/'),
            headers: {'Content-Type': 'application/json'},
            body: jsonEncode({
              'phone_number': phoneNumber,
              'otp': otp,
            }),
          )
          .timeout(const Duration(seconds: 15));

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body) as Map<String, dynamic>;
        await _saveTokens(
          data['access'] as String,
          data['refresh'] as String,
        );
        _currentUser = data['user'] as Map<String, dynamic>?;
      } else {
        final data = jsonDecode(response.body) as Map<String, dynamic>;
        _errorMessage = data['error'] as String? ?? 'Verification failed';
      }
    } catch (e) {
      _errorMessage = 'Network error: $e';
    }

    _isLoading = false;
    notifyListeners();
  }

  Future<void> fetchCurrentUser() async {
    try {
      final response = await http
          .get(
            Uri.parse('$_baseUrl/users/me/'),
            headers: await _authHeaders(),
          )
          .timeout(const Duration(seconds: 15));

      if (response.statusCode == 200) {
        _currentUser = jsonDecode(response.body) as Map<String, dynamic>;
        notifyListeners();
      }
    } catch (_) {}
  }

  Future<void> logout() async {
    await _storage.delete(key: 'access_token');
    await _storage.delete(key: 'refresh_token');
    _accessToken = null;
    _refreshToken = null;
    _currentUser = null;
    notifyListeners();
  }
}
