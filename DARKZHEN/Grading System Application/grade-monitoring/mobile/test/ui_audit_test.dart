import 'dart:convert';
import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:google_fonts/src/google_fonts_base.dart';
import 'package:grade_monitoring_mobile/core/app_state.dart';
import 'package:grade_monitoring_mobile/data/api_client.dart';
import 'package:grade_monitoring_mobile/data/token_storage.dart';
import 'package:grade_monitoring_mobile/domain/models.dart';
import 'package:grade_monitoring_mobile/features/auth/change_password_screen.dart';
import 'package:grade_monitoring_mobile/features/auth/login_screen.dart';
import 'package:grade_monitoring_mobile/features/grades/dashboard_screen.dart';
import 'package:grade_monitoring_mobile/main.dart';
import 'package:provider/provider.dart';

class MemoryTokenStorage extends TokenStorage {
  String? access;
  String? refresh;
  String? userJson;

  @override
  Future<String?> getAccess() async => access;
  @override
  Future<String?> getRefresh() async => refresh;
  @override
  Future<String?> getUserJson() async => userJson;
  @override
  Future<void> saveAccess(String value) async => access = value;
  @override
  Future<void> saveRefresh(String value) async => refresh = value;
  @override
  Future<void> clear() async {
    access = null;
    refresh = null;
    userJson = null;
  }
}

class FakeApiClient extends ApiClient {
  FakeApiClient({required MemoryTokenStorage storage, this.summary}) : super(baseUrl: 'http://localhost', storage: storage);
  final SemesterSummary? summary;

  @override
  Future<SemesterSummary> fetchGrades(int semester) async {
    return summary ?? SemesterSummary(semester: semester, subjects: const []);
  }

  @override
  Future<void> logout() async => storage.clear();
}

void setPhoneSize(WidgetTester tester, Size size) {
  tester.view.physicalSize = size;
  tester.view.devicePixelRatio = 1.0;
  addTearDown(tester.view.reset);
}

MemoryTokenStorage loggedInStorage() {
  return MemoryTokenStorage()
    ..access = 'access'
    ..refresh = 'refresh'
    ..userJson = jsonEncode({'username': '136000000001', 'role': 'student', 'name': 'Juan Miguel Dela Cruz'});
}

SemesterSummary sampleSummary() {
  return SemesterSummary(
    semester: 1,
    generalAverage: 89,
    lastUpdated: DateTime(2026, 11, 10, 8, 30),
    subjects: [
      SubjectGrade(subject: 'General Physics 1', q1: 89, q2: 91, finalGrade: 90),
      SubjectGrade(subject: 'Empowerment Technologies', q1: 87, q2: 89, finalGrade: 88),
      SubjectGrade(subject: 'Practical Research 2', q1: 92, q2: null, finalGrade: null),
    ],
  );
}

Future<void> settleFonts(WidgetTester tester) async {
  await tester.runAsync(() async {
    while (pendingFontFutures.isNotEmpty) {
      await Future.wait(List.of(pendingFontFutures));
    }
  });
  await tester.pumpAndSettle();
}

Future<void> pumpApp(WidgetTester tester, FakeApiClient api) async {
  await tester.pumpWidget(GradeMonitoringApp(api: api));
  await tester.pumpAndSettle();
  await settleFonts(tester);
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  HttpOverrides.global = null;
  setUpAll(() async {
    final icons = FontLoader('MaterialIcons');
    icons.addFont(
      File('C:/flutter/bin/cache/artifacts/material_fonts/materialicons-regular.otf')
          .readAsBytes()
          .then((bytes) => ByteData.view(bytes.buffer)),
    );
    await icons.load();
  });

  testWidgets('mobile login renders without overflow', (tester) async {
    setPhoneSize(tester, const Size(390, 844));
    await pumpApp(tester, FakeApiClient(storage: MemoryTokenStorage()));
    expect(find.byType(LoginScreen), findsOneWidget);
    expect(tester.takeException(), isNull);
    await expectLater(find.byType(LoginScreen), matchesGoldenFile('goldens/ui_audit_login.png'));
  });

  testWidgets('mobile grades render without overflow', (tester) async {
    setPhoneSize(tester, const Size(390, 844));
    await pumpApp(tester, FakeApiClient(storage: loggedInStorage(), summary: sampleSummary()));
    expect(find.byType(DashboardScreen), findsOneWidget);
    expect(find.text('General Average'), findsOneWidget);
    expect(find.text('89'), findsWidgets);
    expect(tester.takeException(), isNull);
    await expectLater(find.byType(HomeShell), matchesGoldenFile('goldens/ui_audit_grades.png'));
  });

  testWidgets('mobile grades fit a narrow phone', (tester) async {
    setPhoneSize(tester, const Size(320, 640));
    await pumpApp(tester, FakeApiClient(storage: loggedInStorage(), summary: sampleSummary()));
    expect(find.byType(DashboardScreen), findsOneWidget);
    expect(tester.takeException(), isNull);
  });

  testWidgets('mobile profile renders without overflow', (tester) async {
    setPhoneSize(tester, const Size(390, 844));
    await pumpApp(tester, FakeApiClient(storage: loggedInStorage(), summary: sampleSummary()));
    await tester.tap(find.text('Profile'));
    await tester.pumpAndSettle();
    expect(find.text('Juan Miguel Dela Cruz'), findsOneWidget);
    expect(tester.takeException(), isNull);
    await expectLater(find.byType(HomeShell), matchesGoldenFile('goldens/ui_audit_profile.png'));
  });

  testWidgets('mobile password change renders without overflow', (tester) async {
    setPhoneSize(tester, const Size(390, 844));
    final state = AppState(api: FakeApiClient(storage: loggedInStorage()));
    await tester.pumpWidget(
      ChangeNotifierProvider.value(
        value: state,
        child: MaterialApp(
          theme: ThemeData(useMaterial3: true, textTheme: GoogleFonts.interTextTheme()),
          home: const ChangePasswordScreen(),
        ),
      ),
    );
    await settleFonts(tester);
    expect(find.text('Save new password'), findsOneWidget);
    expect(tester.takeException(), isNull);
    await expectLater(find.byType(ChangePasswordScreen), matchesGoldenFile('goldens/ui_audit_change_password.png'));
  });
}
