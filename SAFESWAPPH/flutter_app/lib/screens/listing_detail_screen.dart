import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

import '../widgets/listing_card.dart';

class ListingDetailScreen extends StatelessWidget {
  final int id;
  final String title;
  final String robloxUsername;
  final String price;
  final String? screenshotUrl;
  final String sellerName;
  final bool isKycApproved;

  const ListingDetailScreen({
    super.key,
    required this.id,
    required this.title,
    required this.robloxUsername,
    required this.price,
    this.screenshotUrl,
    required this.sellerName,
    this.isKycApproved = false,
  });

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFF4F8FD),
      body: CustomScrollView(
        slivers: [
          _buildSliverAppBar(context),
          SliverToBoxAdapter(child: _buildContent(context)),
          SliverToBoxAdapter(child: _buildSimilarListings()),
        ],
      ),
      bottomNavigationBar: _buildBottomBar(context),
    );
  }

  Widget _buildSliverAppBar(BuildContext context) {
    return SliverAppBar(
      expandedHeight: 260,
      pinned: true,
      backgroundColor: const Color(0xFF185FA5),
      leading: Container(
        margin: const EdgeInsets.all(8),
        decoration: BoxDecoration(
          color: Colors.black.withValues(alpha: 0.3),
          shape: BoxShape.circle,
        ),
        child: IconButton(
          icon: const Icon(Icons.arrow_back_ios_new, color: Colors.white, size: 20),
          onPressed: () => Navigator.pop(context),
        ),
      ),
      flexibleSpace: FlexibleSpaceBar(
        background: _buildHeroImage(),
      ),
    );
  }

  Widget _buildHeroImage() {
    if (screenshotUrl != null && screenshotUrl!.isNotEmpty) {
      return Image.network(
        screenshotUrl!,
        fit: BoxFit.cover,
        errorBuilder: (_, __, ___) => _buildGradientHero(),
      );
    }
    return _buildGradientHero();
  }

  Widget _buildGradientHero() {
    return Container(
      decoration: const BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [Color(0xFF185FA5), Color(0xFF3B2E8A), Color(0xFF2C3E50)],
          stops: [0.0, 0.6, 1.0],
        ),
      ),
      child: Center(
        child: Container(
          width: 72,
          height: 72,
          decoration: BoxDecoration(
            color: Colors.white.withValues(alpha: 0.15),
            borderRadius: BorderRadius.circular(20),
          ),
          child: const Icon(
            Icons.shield_outlined,
            color: Colors.white,
            size: 38,
          ),
        ),
      ),
    );
  }

  Widget _buildContent(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.all(20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            title,
            style: GoogleFonts.poppins(
              fontSize: 22,
              fontWeight: FontWeight.w700,
              color: const Color(0xFF1A1A2E),
            ),
          ),
          const SizedBox(height: 6),
          Row(
            children: [
              const Icon(Icons.gamepad_outlined, size: 16, color: Color(0xFF6B7280)),
              const SizedBox(width: 6),
              Text(
                robloxUsername,
                style: GoogleFonts.poppins(
                  fontSize: 14,
                  color: const Color(0xFF6B7280),
                ),
              ),
              const Spacer(),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                decoration: BoxDecoration(
                  color: const Color(0xFFFEE2E2),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Text(
                  'Roblox',
                  style: GoogleFonts.poppins(
                    fontSize: 10,
                    fontWeight: FontWeight.w600,
                    color: const Color(0xFFDC2626),
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 20),
          Container(
            width: double.infinity,
            padding: const EdgeInsets.all(20),
            decoration: BoxDecoration(
              gradient: const LinearGradient(
                colors: [Color(0xFF185FA5), Color(0xFF534AB7)],
              ),
              borderRadius: BorderRadius.circular(20),
              boxShadow: [
                BoxShadow(
                  color: const Color(0xFF185FA5).withValues(alpha: 0.25),
                  blurRadius: 20,
                  offset: const Offset(0, 8),
                ),
              ],
            ),
            child: Column(
              children: [
                Text(
                  'Price',
                  style: GoogleFonts.poppins(
                    fontSize: 12,
                    color: Colors.white.withValues(alpha: 0.7),
                    letterSpacing: 1,
                  ),
                ),
                const SizedBox(height: 4),
                Text(
                  price,
                  style: GoogleFonts.poppins(
                    fontSize: 34,
                    fontWeight: FontWeight.w800,
                    color: Colors.white,
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 20),
          Container(
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              color: Colors.white,
              borderRadius: BorderRadius.circular(16),
              boxShadow: [
                BoxShadow(
                  color: Colors.black.withValues(alpha: 0.04),
                  blurRadius: 16,
                  offset: const Offset(0, 4),
                ),
              ],
            ),
            child: Row(
              children: [
                CircleAvatar(
                  radius: 22,
                  backgroundColor: const Color(0xFF185FA5),
                  child: Text(
                    sellerName.isNotEmpty ? sellerName[0].toUpperCase() : '?',
                    style: GoogleFonts.poppins(
                      color: Colors.white,
                      fontWeight: FontWeight.w600,
                      fontSize: 18,
                    ),
                  ),
                ),
                const SizedBox(width: 14),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        children: [
                          Text(
                            sellerName,
                            style: GoogleFonts.poppins(
                              fontSize: 15,
                              fontWeight: FontWeight.w600,
                              color: const Color(0xFF1A1A2E),
                            ),
                          ),
                          if (isKycApproved) ...[
                            const SizedBox(width: 6),
                            const Icon(Icons.verified_rounded, color: Colors.green, size: 18),
                          ],
                        ],
                      ),
                      Text(
                        'Seller',
                        style: GoogleFonts.poppins(
                          fontSize: 12,
                          color: const Color(0xFF6B7280),
                        ),
                      ),
                    ],
                  ),
                ),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                  decoration: BoxDecoration(
                    color: isKycApproved
                        ? const Color(0xFFD1FAE5)
                        : const Color(0xFFFEF3C7),
                    borderRadius: BorderRadius.circular(20),
                  ),
                  child: Text(
                    isKycApproved ? 'Verified' : 'Pending',
                    style: GoogleFonts.poppins(
                      fontSize: 10,
                      fontWeight: FontWeight.w600,
                      color: isKycApproved
                          ? const Color(0xFF065F46)
                          : const Color(0xFF92400E),
                    ),
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 20),
          Text(
            'Description',
            style: GoogleFonts.poppins(
              fontSize: 16,
              fontWeight: FontWeight.w600,
              color: const Color(0xFF1A1A2E),
            ),
          ),
          const SizedBox(height: 8),
          Text(
            'A great Roblox account with rare items and high level. This account has been verified and is ready for transfer via middleman.',
            style: GoogleFonts.poppins(
              fontSize: 13,
              color: const Color(0xFF6B7280),
              height: 1.7,
            ),
          ),
          const SizedBox(height: 20),
          _buildInfoRow(Icons.shield_outlined, 'Middleman Protection', 'Your payment is held in escrow'),
          const SizedBox(height: 12),
          _buildInfoRow(Icons.verified_user_outlined, 'Secure Transfer', 'Account credentials sent after confirmation'),
        ],
      ),
    );
  }

  Widget _buildInfoRow(IconData icon, String title, String subtitle) {
    return Row(
      children: [
        Container(
          width: 40,
          height: 40,
          decoration: BoxDecoration(
            color: const Color(0xFF185FA5).withValues(alpha: 0.08),
            borderRadius: BorderRadius.circular(10),
          ),
          child: Icon(icon, color: const Color(0xFF185FA5), size: 20),
        ),
        const SizedBox(width: 12),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                title,
                style: GoogleFonts.poppins(
                  fontSize: 13,
                  fontWeight: FontWeight.w600,
                  color: const Color(0xFF1A1A2E),
                ),
              ),
              Text(
                subtitle,
                style: GoogleFonts.poppins(
                  fontSize: 11,
                  color: const Color(0xFF6B7280),
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }

  Widget _buildSimilarListings() {
    return Padding(
      padding: const EdgeInsets.fromLTRB(20, 8, 20, 100),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(
                'Similar Listings',
                style: GoogleFonts.poppins(
                  fontSize: 16,
                  fontWeight: FontWeight.w600,
                  color: const Color(0xFF1A1A2E),
                ),
              ),
              TextButton(
                onPressed: () {},
                child: Text(
                  'See All',
                  style: GoogleFonts.poppins(
                    fontSize: 12,
                    color: const Color(0xFF185FA5),
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),
          SizedBox(
            height: 230,
            child: ListView.separated(
              scrollDirection: Axis.horizontal,
              itemCount: 3,
              separatorBuilder: (_, __) => const SizedBox(width: 12),
              itemBuilder: (_, i) => SizedBox(
                width: 180,
                child: ListingCard(
                  id: i + 10,
                  title: 'Similar Listing ${i + 1}',
                  robloxUsername: 'player_${i + 10}',
                  price: '₱${(i + 1) * 300}',
                  sellerName: 'Seller ${i + 1}',
                  isKycApproved: i % 2 == 0,
                  onTap: () {},
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildBottomBar(BuildContext context) {
    return Container(
      padding: EdgeInsets.only(
        left: 20,
        right: 20,
        top: 12,
        bottom: MediaQuery.of(context).padding.bottom + 12,
      ),
      decoration: const BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.only(
          topLeft: Radius.circular(20),
          topRight: Radius.circular(20),
        ),
        boxShadow: [
          BoxShadow(
            color: Color(0x0A000000),
            blurRadius: 16,
            offset: Offset(0, -4),
          ),
        ],
      ),
      child: Row(
        children: [
          Expanded(
            child: OutlinedButton(
              onPressed: () {},
              style: OutlinedButton.styleFrom(
                foregroundColor: const Color(0xFF185FA5),
                side: const BorderSide(color: Color(0xFF185FA5)),
                minimumSize: const Size(0, 54),
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(14),
                ),
              ),
              child: Text(
                'Message Seller',
                style: GoogleFonts.poppins(fontWeight: FontWeight.w600),
              ),
            ),
          ),
          const SizedBox(width: 12),
          Expanded(
            flex: 2,
            child: ElevatedButton.icon(
              onPressed: () {},
              icon: const Icon(Icons.shield_outlined, size: 20),
              label: Text(
                'Start Trade',
                style: GoogleFonts.poppins(fontWeight: FontWeight.w600),
              ),
              style: ElevatedButton.styleFrom(
                minimumSize: const Size(0, 54),
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(14),
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}
