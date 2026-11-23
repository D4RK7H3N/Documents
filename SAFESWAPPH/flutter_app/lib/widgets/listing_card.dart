import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

class ListingCard extends StatelessWidget {
  final int id;
  final String title;
  final String robloxUsername;
  final String price;
  final String? screenshotUrl;
  final String sellerName;
  final bool isKycApproved;
  final String? sellerAvatar;
  final VoidCallback? onTap;

  const ListingCard({
    super.key,
    required this.id,
    required this.title,
    required this.robloxUsername,
    required this.price,
    this.screenshotUrl,
    required this.sellerName,
    this.isKycApproved = false,
    this.sellerAvatar,
    this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        decoration: BoxDecoration(
          color: Colors.white,
          borderRadius: BorderRadius.circular(16),
          border: Border.all(color: const Color(0xFFE5E7EB)),
        ),
        clipBehavior: Clip.antiAlias,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            _buildThumbnail(),
            Padding(
              padding: const EdgeInsets.all(12),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    title,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: GoogleFonts.poppins(
                      fontSize: 14,
                      fontWeight: FontWeight.w600,
                      color: const Color(0xFF1A1A2E),
                    ),
                  ),
                  const SizedBox(height: 4),
                  Row(
                    children: [
                      const Icon(Icons.gamepad, size: 12, color: Color(0xFF6B7280)),
                      const SizedBox(width: 4),
                      Expanded(
                        child: Text(
                          robloxUsername,
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                          style: GoogleFonts.poppins(
                            fontSize: 12,
                            color: const Color(0xFF6B7280),
                          ),
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 8),
                  Text(
                    price,
                    style: GoogleFonts.poppins(
                      fontSize: 16,
                      fontWeight: FontWeight.w700,
                      color: const Color(0xFF185FA5),
                    ),
                  ),
                  const SizedBox(height: 8),
                  Row(
                    children: [
                      CircleAvatar(
                        radius: 10,
                        backgroundColor: const Color(0xFF185FA5),
                        child: Text(
                          sellerName.isNotEmpty ? sellerName[0].toUpperCase() : '?',
                          style: GoogleFonts.poppins(
                            fontSize: 10,
                            color: Colors.white,
                            fontWeight: FontWeight.w600,
                          ),
                        ),
                      ),
                      const SizedBox(width: 6),
                      Expanded(
                        child: Text(
                          sellerName,
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                          style: GoogleFonts.poppins(
                            fontSize: 11,
                            color: const Color(0xFF6B7280),
                          ),
                        ),
                      ),
                      if (isKycApproved)
                        const Icon(Icons.verified, color: Colors.green, size: 14),
                    ],
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildThumbnail() {
    if (screenshotUrl != null && screenshotUrl!.isNotEmpty) {
      return Image.network(
        screenshotUrl!,
        height: 120,
        width: double.infinity,
        fit: BoxFit.cover,
        errorBuilder: (_, __, ___) => _placeholderGradient(),
      );
    }
    return _placeholderGradient();
  }

  Widget _placeholderGradient() {
    return Container(
      height: 120,
      width: double.infinity,
      decoration: const BoxDecoration(
        gradient: LinearGradient(
          colors: [Color(0xFF185FA5), Color(0xFF534AB7)],
        ),
      ),
      child: const Center(
        child: Icon(Icons.image, color: Colors.white38, size: 40),
      ),
    );
  }
}
