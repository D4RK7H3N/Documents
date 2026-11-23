import 'package:flutter_test/flutter_test.dart';
import 'package:grade_monitoring_mobile/domain/models.dart';

void main() {
  test('AppUser round-trips profile fields through JSON', () {
    final user = AppUser.fromJson({
      'username': '123456789012',
      'role': 'student',
      'name': 'Juan Dela Cruz',
      'email': 'juan@example.com',
      'phone': '09171234567',
      'avatar_url': 'https://example.com/media/avatars/a.png',
    });
    expect(user.email, 'juan@example.com');
    expect(user.phone, '09171234567');
    expect(user.avatarUrl, isNotNull);

    final restored = AppUser.fromJson(user.toJson());
    expect(restored.username, '123456789012');
    expect(restored.email, 'juan@example.com');
    expect(restored.avatarUrl, user.avatarUrl);
  });

  test('copyWith preserves fields and can clear the avatar', () {
    const user = AppUser(username: 'u', role: 'student', name: 'n', email: 'e@x.com', avatarUrl: 'url');
    final cleared = user.copyWith(clearAvatar: true);
    expect(cleared.avatarUrl, isNull);
    expect(cleared.email, 'e@x.com');
    final updated = user.copyWith(phone: '0999');
    expect(updated.phone, '0999');
    expect(updated.avatarUrl, 'url');
  });
}
