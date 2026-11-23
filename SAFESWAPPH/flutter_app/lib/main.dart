import 'package:firebase_core/firebase_core.dart';
import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:provider/provider.dart';

import 'providers/auth_provider.dart';
import 'providers/kyc_provider.dart';
import 'screens/chat_screen.dart';
import 'screens/create_listing_screen.dart';
import 'screens/home_screen.dart';
import 'screens/kyc_screen.dart';
import 'screens/kyc_required_screen.dart';
import 'screens/listing_detail_screen.dart';
import 'screens/login_screen.dart';
import 'screens/onboarding_screen.dart';
import 'screens/otp_screen.dart';
import 'screens/payment_screen.dart';
import 'screens/profile_screen.dart';
import 'screens/register_screen.dart';
import 'screens/splash_screen.dart';
import 'screens/tos_screen.dart';
import 'screens/welcome_screen.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  try {
    await Firebase.initializeApp();
  } catch (_) {
    // Firebase not configured — push notifications disabled
  }
  runApp(
    MultiProvider(
      providers: [
        ChangeNotifierProvider(create: (_) => AuthProvider()),
        ChangeNotifierProvider(create: (_) => KYCProvider()),
      ],
      child: const SafeSwapApp(),
    ),
  );
}

class _SlideRoute extends PageRouteBuilder {
  final Widget page;
  _SlideRoute(this.page)
      : super(
          transitionDuration: const Duration(milliseconds: 300),
          pageBuilder: (_, __, ___) => page,
          transitionsBuilder: (_, anim, __, child) =>
              SlideTransition(
                position: Tween<Offset>(
                  begin: const Offset(0.15, 0),
                  end: Offset.zero,
                ).animate(CurvedAnimation(
                  parent: anim,
                  curve: Curves.easeOutCubic,
                )),
                child: FadeTransition(
                  opacity: anim,
                  child: child,
                ),
              ),
        );
}

class SafeSwapApp extends StatelessWidget {
  const SafeSwapApp({super.key});

  @override
  Widget build(BuildContext context) {
    final theme = ThemeData(
      useMaterial3: true,
      scaffoldBackgroundColor: const Color(0xFFF4F8FD),
      colorScheme: ColorScheme.fromSeed(
        seedColor: const Color(0xFF185FA5),
        primary: const Color(0xFF185FA5),
        secondary: const Color(0xFF534AB7),
        tertiary: const Color(0xFF0F6E56),
        surface: Colors.white,
      ),
      primaryColor: const Color(0xFF185FA5),
      appBarTheme: AppBarTheme(
        backgroundColor: Colors.white,
        foregroundColor: const Color(0xFF1A1A2E),
        elevation: 0,
        centerTitle: true,
        titleTextStyle: GoogleFonts.poppins(
          fontSize: 18,
          fontWeight: FontWeight.w600,
          color: const Color(0xFF1A1A2E),
        ),
      ),
      elevatedButtonTheme: ElevatedButtonThemeData(
        style: ElevatedButton.styleFrom(
          backgroundColor: const Color(0xFF185FA5),
          foregroundColor: Colors.white,
          minimumSize: const Size(double.infinity, 54),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(14),
          ),
          textStyle: GoogleFonts.poppins(
            fontSize: 15,
            fontWeight: FontWeight.w600,
          ),
          elevation: 0,
        ),
      ),
      inputDecorationTheme: InputDecorationTheme(
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(14),
          borderSide: const BorderSide(color: Color(0xFFE5E7EB)),
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(14),
          borderSide: const BorderSide(color: Color(0xFFE5E7EB)),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(14),
          borderSide: const BorderSide(color: Color(0xFF185FA5), width: 2),
        ),
        filled: true,
        fillColor: Colors.white,
        contentPadding: const EdgeInsets.symmetric(
          horizontal: 18,
          vertical: 16,
        ),
        hintStyle: GoogleFonts.poppins(
          fontSize: 14,
          color: const Color(0xFF9CA3AF),
        ),
        labelStyle: GoogleFonts.poppins(
          fontSize: 14,
          fontWeight: FontWeight.w500,
          color: const Color(0xFF6B7280),
        ),
      ),
      fontFamily: GoogleFonts.poppins().fontFamily,
    );

    return MaterialApp(
      title: 'SafeSwap PH',
      debugShowCheckedModeBanner: false,
      theme: theme,
      initialRoute: '/splash',
      onGenerateRoute: (settings) {
        final routes = <String, Widget Function()>{
          '/splash': () => const SplashScreen(),
          '/welcome': () => const WelcomeScreen(),
          '/register': () => const RegisterScreen(),
          '/login': () => const LoginScreen(),
          '/otp': () => const OTPScreen(),
          '/kyc-required': () => const KYCRequiredScreen(),
          '/home': () => const HomeScreen(),
          '/kyc': () => const KYCScreen(),
          '/create-listing': () => const CreateListingScreen(),
          '/profile': () => const ProfileScreen(),
          '/tos': () => const TOSScreen(),
          '/onboarding': () => const OnboardingScreen(),
        };
        final builder = routes[settings.name];
        if (builder != null) return _SlideRoute(builder());
        if (settings.name == '/listing-detail' && settings.arguments is Map) {
          final args = settings.arguments as Map<String, dynamic>;
          return _SlideRoute(ListingDetailScreen(
            id: args['id'] as int,
            title: args['title'] as String,
            robloxUsername: args['roblox_username'] as String,
            price: args['price'] as String,
            screenshotUrl: args['screenshot_url'] as String?,
            sellerName: args['seller_name'] as String,
            isKycApproved: args['is_kyc_approved'] as bool? ?? false,
          ));
        }
        if (settings.name == '/chat' && settings.arguments is Map) {
          final args = settings.arguments as Map<String, dynamic>;
          return _SlideRoute(ChatScreen(
            conversationId: args['conversation_id'] as int,
            tradeId: args['trade_id'] as int,
            tradeTitle: args['trade_title'] as String,
          ));
        }
        if (settings.name == '/payment' && settings.arguments is Map) {
          final args = settings.arguments as Map<String, dynamic>;
          return _SlideRoute(PaymentScreen(
            tradeId: args['trade_id'] as int,
            amount: args['amount'] as String,
          ));
        }
        return null;
      },
    );
  }
}
