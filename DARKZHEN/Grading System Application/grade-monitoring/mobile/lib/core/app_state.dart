import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:flutter/material.dart';

import '../data/api_client.dart';
import '../domain/models.dart';

class SessionExpiredEvent {
  static final stream = StreamController<void>.broadcast();
}

class AppState extends ChangeNotifier {
  final ApiClient api;
  AppUser? user;
  bool mustChangePassword = false;
  bool initialized = false;
  bool busy = false;

  AppState({required this.api}) {
    SessionExpiredEvent.stream.stream.listen((_) {
      user = null;
      mustChangePassword = false;
      notifyListeners();
    });
  }

  Future<void> bootstrap() async {
    final userJson = await api.storage.getUserJson();
    final hasSession = await api.storage.getRefresh() != null;
    if (hasSession && userJson != null && userJson.isNotEmpty) {
      try {
        user = AppUser.fromJson(jsonDecode(userJson) as Map<String, dynamic>);
        mustChangePassword = false;
      } catch (_) {
        user = null;
      }
    }
    initialized = true;
    notifyListeners();
  }

  Future<String?> login(String username, String password) async {
    busy = true;
    notifyListeners();
    try {
      final result = await api.login(username, password);
      user = result.user;
      mustChangePassword = result.mustChangePassword;
      notifyListeners();
      return null;
    } on ApiException catch (e) {
      return e.message;
    } catch (_) {
      return 'Network error. Check your connection and try again.';
    } finally {
      busy = false;
      notifyListeners();
    }
  }

  Future<String?> changePassword(String current, String next) async {
    busy = true;
    notifyListeners();
    try {
      await api.changePassword(current, next);
      await api.storage.clear();
      user = null;
      mustChangePassword = false;
      notifyListeners();
      return null;
    } on ApiException catch (e) {
      return e.message;
    } catch (_) {
      return 'Network error. Please try again.';
    } finally {
      busy = false;
      notifyListeners();
    }
  }

  Future<void> logout() async {
    await api.logout();
    user = null;
    mustChangePassword = false;
    notifyListeners();
  }

  Future<String?> saveProfile({required String email, required String phone}) async {
    busy = true;
    notifyListeners();
    try {
      user = await api.updateProfile(email: email, phone: phone);
      await api.storage.saveUserJson(jsonEncode(user!.toJson()));
      notifyListeners();
      return null;
    } on ApiException catch (e) {
      return e.message;
    } catch (_) {
      return 'Network error. Please try again.';
    } finally {
      busy = false;
      notifyListeners();
    }
  }

  Future<String?> updateAvatarPhoto(File file) async {
    try {
      final url = await api.uploadAvatar(file);
      final current = user;
      if (current != null) {
        user = current.copyWith(avatarUrl: url);
        await api.storage.saveUserJson(jsonEncode(user!.toJson()));
        notifyListeners();
      }
      return null;
    } on ApiException catch (e) {
      return e.message;
    } catch (_) {
      return 'Network error. Please try again.';
    }
  }

  Future<String?> removeAvatarPhoto() async {
    try {
      await api.removeAvatar();
      final current = user;
      if (current != null) {
        user = current.copyWith(clearAvatar: true);
        await api.storage.saveUserJson(jsonEncode(user!.toJson()));
        notifyListeners();
      }
      return null;
    } on ApiException catch (e) {
      return e.message;
    } catch (_) {
      return 'Network error. Please try again.';
    }
  }
}
