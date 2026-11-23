import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:provider/provider.dart';

import 'core/app_state.dart';
import 'data/api_client.dart';
import 'data/token_storage.dart';
import 'features/auth/change_password_screen.dart';
import 'features/auth/login_screen.dart';
import 'features/grades/dashboard_screen.dart';
import 'features/settings/profile_screen.dart';

const appBaseUrl = String.fromEnvironment('API_BASE_URL',
    defaultValue: 'http://10.0.2.2:8000');

void main() {
  final storage = TokenStorage();
  final api = ApiClient(baseUrl: appBaseUrl, storage: storage);
  runApp(GradeMonitoringApp(api: api));
}

class GradeMonitoringApp extends StatelessWidget {
  final ApiClient api;

  const GradeMonitoringApp({super.key, required this.api});

  @override
  Widget build(BuildContext context) {
    const colorScheme = ColorScheme.light(
      primary: Color(0xFF263C52),
      onPrimary: Colors.white,
      primaryContainer: Color(0xFFD9EBF5),
      onPrimaryContainer: Color(0xFF17232D),
      secondary: Color(0xFF3A6880),
      onSecondary: Colors.white,
      secondaryContainer: Color(0xFFD9EBF5),
      onSecondaryContainer: Color(0xFF263C52),
      surface: Color(0xFFEAF3F8),
      onSurface: Color(0xFF17232D),
      surfaceContainerLowest: Colors.white,
      surfaceContainerLow: Color(0xFFF4F8FB),
      surfaceContainer: Color(0xFFE3EFF5),
      surfaceContainerHigh: Color(0xFFD9EBF5),
      surfaceContainerHighest: Color(0xFFC9E2F0),
      onSurfaceVariant: Color(0xFF566573),
      outline: Color(0xFF3A6880),
      outlineVariant: Color(0xFFD2E0E8),
      error: Color(0xFFB42318),
      onError: Colors.white,
      errorContainer: Color(0xFFFDECEA),
      onErrorContainer: Color(0xFF7A271A),
    );

    return ChangeNotifierProvider(
      create: (_) => AppState(api: api)..bootstrap(),
      child: Consumer<AppState>(
        builder: (context, state, _) {
          Widget home;
          if (!state.initialized) {
            home = const Scaffold(
                body: Center(child: CircularProgressIndicator()));
          } else if (state.user == null) {
            home = const LoginScreen();
          } else if (state.mustChangePassword) {
            home = const ChangePasswordScreen();
          } else {
            home = const HomeShell();
          }
          return MaterialApp(
            title: 'Grades',
            debugShowCheckedModeBanner: false,
            theme: ThemeData(
              useMaterial3: true,
              colorScheme: colorScheme,
              scaffoldBackgroundColor: colorScheme.surface,
              textTheme: GoogleFonts.interTextTheme().copyWith(
                headlineSmall: GoogleFonts.plusJakartaSans(
                  fontWeight: FontWeight.w700,
                  letterSpacing: -0.5,
                  color: colorScheme.onSurface,
                ),
                titleLarge: GoogleFonts.plusJakartaSans(
                  fontWeight: FontWeight.w700,
                  letterSpacing: -0.3,
                  color: colorScheme.onSurface,
                ),
                titleMedium: GoogleFonts.plusJakartaSans(
                  fontWeight: FontWeight.w600,
                  color: colorScheme.onSurface,
                ),
              ),
              appBarTheme: AppBarTheme(
                elevation: 0,
                backgroundColor: colorScheme.primary,
                foregroundColor: colorScheme.onPrimary,
                surfaceTintColor: Colors.transparent,
                titleTextStyle: GoogleFonts.plusJakartaSans(
                  fontSize: 20,
                  fontWeight: FontWeight.w700,
                  color: colorScheme.onPrimary,
                  letterSpacing: -0.3,
                ),
              ),
              cardTheme: CardThemeData(
                elevation: 0,
                color: colorScheme.surfaceContainerLowest,
                shape: RoundedRectangleBorder(
                  side: BorderSide(color: colorScheme.outlineVariant),
                  borderRadius: BorderRadius.circular(12),
                ),
                margin: EdgeInsets.zero,
              ),
              inputDecorationTheme: InputDecorationTheme(
                filled: true,
                fillColor: colorScheme.surfaceContainerLow,
                labelStyle: TextStyle(color: colorScheme.onSurfaceVariant),
                floatingLabelStyle: TextStyle(color: colorScheme.primary),
                helperStyle: TextStyle(color: colorScheme.onSurfaceVariant),
                contentPadding:
                    const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
                border: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(8),
                  borderSide: BorderSide(color: colorScheme.outlineVariant),
                ),
                enabledBorder: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(8),
                  borderSide: BorderSide(color: colorScheme.outlineVariant),
                ),
                focusedBorder: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(8),
                  borderSide: BorderSide(color: colorScheme.secondary, width: 2),
                ),
                errorBorder: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(8),
                  borderSide: BorderSide(color: colorScheme.error),
                ),
                focusedErrorBorder: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(8),
                  borderSide: BorderSide(color: colorScheme.error, width: 2),
                ),
              ),
              filledButtonTheme: FilledButtonThemeData(
                style: FilledButton.styleFrom(
                  backgroundColor: colorScheme.primary,
                  foregroundColor: colorScheme.onPrimary,
                  minimumSize: const Size(64, 48),
                  padding: const EdgeInsets.symmetric(horizontal: 20),
                  shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(8)),
                  textStyle: const TextStyle(fontWeight: FontWeight.w600),
                ),
              ),
              outlinedButtonTheme: OutlinedButtonThemeData(
                style: OutlinedButton.styleFrom(
                  foregroundColor: colorScheme.primary,
                  minimumSize: const Size(64, 48),
                  side: BorderSide(color: colorScheme.outlineVariant),
                  shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(8)),
                  textStyle: const TextStyle(fontWeight: FontWeight.w600),
                ),
              ),
              textButtonTheme: TextButtonThemeData(
                style: TextButton.styleFrom(
                  foregroundColor: colorScheme.primary,
                  minimumSize: const Size(64, 48),
                ),
              ),
              iconButtonTheme: const IconButtonThemeData(
                style: ButtonStyle(
                    minimumSize: WidgetStatePropertyAll(Size(48, 48))),
              ),
              segmentedButtonTheme: SegmentedButtonThemeData(
                style: SegmentedButton.styleFrom(
                  backgroundColor: colorScheme.surfaceContainerLowest,
                  foregroundColor: colorScheme.onSurfaceVariant,
                  selectedBackgroundColor: colorScheme.secondaryContainer,
                  selectedForegroundColor: colorScheme.onSurface,
                  minimumSize: const Size(0, 48),
                  side: BorderSide(color: colorScheme.outlineVariant),
                  shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(8)),
                  textStyle: const TextStyle(
                      fontSize: 13, fontWeight: FontWeight.w600),
                ),
              ),
              snackBarTheme: SnackBarThemeData(
                behavior: SnackBarBehavior.floating,
                backgroundColor: colorScheme.primary,
                contentTextStyle: TextStyle(color: colorScheme.onPrimary),
                shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(8)),
              ),
              dialogTheme: DialogThemeData(
                backgroundColor: colorScheme.surfaceContainerLowest,
                titleTextStyle: GoogleFonts.plusJakartaSans(
                  fontSize: 20,
                  fontWeight: FontWeight.w700,
                  color: colorScheme.onSurface,
                ),
                shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(12)),
              ),
              dividerTheme: DividerThemeData(color: colorScheme.outlineVariant),
              progressIndicatorTheme:
                  ProgressIndicatorThemeData(color: colorScheme.primary),
              navigationBarTheme: NavigationBarThemeData(
                height: 68,
                backgroundColor: colorScheme.surfaceContainerLowest,
                surfaceTintColor: Colors.transparent,
                indicatorColor: colorScheme.secondaryContainer,
                iconTheme: WidgetStateProperty.resolveWith(
                  (states) => IconThemeData(
                    color: states.contains(WidgetState.selected)
                        ? colorScheme.primary
                        : colorScheme.onSurfaceVariant,
                  ),
                ),
                labelTextStyle: WidgetStateProperty.resolveWith(
                  (states) => TextStyle(
                    fontSize: 11,
                    fontWeight: states.contains(WidgetState.selected)
                        ? FontWeight.w700
                        : FontWeight.w500,
                    color: states.contains(WidgetState.selected)
                        ? colorScheme.primary
                        : colorScheme.onSurfaceVariant,
                  ),
                ),
              ),
            ),
            home: home,
          );
        },
      ),
    );
  }
}

class HomeShell extends StatefulWidget {
  const HomeShell({super.key});

  @override
  State<HomeShell> createState() => _HomeShellState();
}

class _HomeShellState extends State<HomeShell> {
  int _index = 0;

  @override
  Widget build(BuildContext context) {
    final screens = [const DashboardScreen(), const ProfileScreen()];
    return Scaffold(
      body: screens[_index],
      bottomNavigationBar: NavigationBar(
        selectedIndex: _index,
        onDestinationSelected: (i) => setState(() => _index = i),
        destinations: const [
          NavigationDestination(
              icon: Icon(Icons.grade_outlined),
              selectedIcon: Icon(Icons.grade),
              label: 'Grades'),
          NavigationDestination(
              icon: Icon(Icons.person_outline),
              selectedIcon: Icon(Icons.person),
              label: 'Profile'),
        ],
      ),
    );
  }
}
