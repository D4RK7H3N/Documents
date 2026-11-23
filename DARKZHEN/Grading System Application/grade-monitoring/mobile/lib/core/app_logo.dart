import 'package:flutter/material.dart';

class AppLogo extends StatelessWidget {
  final double size;

  const AppLogo({super.key, this.size = 48});

  @override
  Widget build(BuildContext context) {
    return Container(
      width: size,
      height: size,
      decoration: BoxDecoration(
        color: const Color(0xFF263C52),
        borderRadius: BorderRadius.circular(size * 0.25),
      ),
      child: Icon(Icons.school, color: Colors.white, size: size * 0.58),
    );
  }
}
