import 'dart:async';

import 'package:flutter_secure_storage/flutter_secure_storage.dart';

class TokenStorage {
  static const _accessKey = 'access_token';
  static const _refreshKey = 'refresh_token';
  static const _userKey = 'user_json';

  final _storage = const FlutterSecureStorage();

  Future<String?> getAccess() => _storage.read(key: _accessKey);
  Future<String?> getRefresh() => _storage.read(key: _refreshKey);
  Future<String?> getUserJson() => _storage.read(key: _userKey);

  Future<void> save({required String access, required String refresh, required String userJson}) async {
    await _storage.write(key: _accessKey, value: access);
    await _storage.write(key: _refreshKey, value: refresh);
    await _storage.write(key: _userKey, value: userJson);
  }

  Future<void> saveAccess(String access) => _storage.write(key: _accessKey, value: access);
  Future<void> saveRefresh(String refresh) => _storage.write(key: _refreshKey, value: refresh);
  Future<void> saveUserJson(String userJson) => _storage.write(key: _userKey, value: userJson);

  Future<void> clear() async {
    await _storage.delete(key: _accessKey);
    await _storage.delete(key: _refreshKey);
    await _storage.delete(key: _userKey);
  }
}
