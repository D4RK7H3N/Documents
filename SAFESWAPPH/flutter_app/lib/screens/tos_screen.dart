import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:http/http.dart' as http;
import 'package:provider/provider.dart';

import '../providers/auth_provider.dart';

class TOSScreen extends StatefulWidget {
  final bool showAcceptButton;

  const TOSScreen({super.key, this.showAcceptButton = true});

  @override
  State<TOSScreen> createState() => _TOSScreenState();
}

class _TOSScreenState extends State<TOSScreen> {
  static const _baseUrl = 'http://10.0.2.2:8000/api';

  final _scrollController = ScrollController();
  String? _content;
  String? _version;
  int? _tosId;
  bool _isLoading = true;
  bool _hasScrolledToBottom = false;
  bool _isAccepting = false;
  bool _alreadyAccepted = false;

  @override
  void initState() {
    super.initState();
    _scrollController.addListener(_onScroll);
    _loadTOS();
  }

  void _onScroll() {
    if (_scrollController.position.pixels >=
        _scrollController.position.maxScrollExtent - 20) {
      if (!_hasScrolledToBottom) {
        setState(() => _hasScrolledToBottom = true);
      }
    }
  }

  Future<void> _loadTOS() async {
    final auth = context.read<AuthProvider>();
    final token = auth.accessToken;
    if (token == null) return;

    try {
      final uri = Uri.parse('$_baseUrl/tos/check/');
      final response = await http.get(uri, headers: {
        'Authorization': 'Bearer $token',
      });
      if (response.statusCode == 200) {
        final body = jsonDecode(response.body);
        setState(() {
          _content = body['content'] as String?;
          _version = body['version'] as String?;
          _tosId = body['tos_id'] as int?;
          _alreadyAccepted = body['accepted'] as bool? ?? false;
          if (_alreadyAccepted) _hasScrolledToBottom = true;
          _isLoading = false;
        });
      } else {
        setState(() => _isLoading = false);
      }
    } catch (_) {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  Future<void> _acceptTOS() async {
    if (_isAccepting || _tosId == null) return;
    setState(() => _isAccepting = true);

    final auth = context.read<AuthProvider>();
    final token = auth.accessToken;
    if (token == null) return;

    try {
      await http.post(
        Uri.parse('$_baseUrl/tos/accept/'),
        headers: {
          'Authorization': 'Bearer $token',
          'Content-Type': 'application/json',
        },
        body: jsonEncode({'tos_id': _tosId}),
      );
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Terms accepted!')),
        );
        Navigator.pop(context, true);
      }
    } catch (_) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Failed to accept TOS. Try again.')),
        );
      }
    } finally {
      if (mounted) setState(() => _isAccepting = false);
    }
  }

  @override
  void dispose() {
    _scrollController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFF4F8FD),
      appBar: AppBar(
        title: Text('Terms of Service',
          style: GoogleFonts.poppins(fontWeight: FontWeight.w600)),
        actions: [
          if (_alreadyAccepted)
            Padding(
              padding: EdgeInsets.only(right: 12),
              child: Icon(Icons.check_circle, color: Colors.green, size: 22),
            ),
        ],
      ),
      body: _isLoading
          ? Center(child: CircularProgressIndicator())
          : _content == null
              ? Center(child: Text('No TOS available',
                  style: GoogleFonts.poppins(color: Colors.grey)))
              : Column(
                  children: [
                    if (_version != null)
                      Container(
                        width: double.infinity,
                        padding: EdgeInsets.symmetric(horizontal: 20, vertical: 12),
                        color: Color(0xFF185FA5).withValues(alpha: 0.06),
                        child: Text('Version $_version',
                          style: GoogleFonts.poppins(
                            fontSize: 12,
                            fontWeight: FontWeight.w600,
                            color: Color(0xFF185FA5),
                          )),
                      ),
                    Expanded(
                      child: SingleChildScrollView(
                        controller: _scrollController,
                        padding: EdgeInsets.all(20),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              'SafeSwap PH — Trader Terms of Service',
                              style: GoogleFonts.poppins(
                                fontSize: 20,
                                fontWeight: FontWeight.w700,
                                color: Color(0xFF1A1A2E),
                              ),
                            ),
                            SizedBox(height: 20),
                            ...(_buildSections()),
                            SizedBox(height: 40),
                          ],
                        ),
                      ),
                    ),
                    if (widget.showAcceptButton && !_alreadyAccepted)
                      _buildBottomBar(),
                  ],
                ),
    );
  }

  List<Widget> _buildSections() {
    if (_content == null) return [];
    final paragraphs = _content!.split('\n\n');
    return paragraphs.where((p) => p.trim().isNotEmpty).map((p) {
      if (p.startsWith('## ')) {
        return Padding(
          padding: EdgeInsets.only(top: 20, bottom: 8),
          child: Text(
            p.replaceAll('## ', ''),
            style: GoogleFonts.poppins(
              fontSize: 16,
              fontWeight: FontWeight.w700,
              color: Color(0xFF1A1A2E),
            ),
          ),
        );
      }
      if (p.startsWith('**') && p.endsWith('**')) {
        return Padding(
          padding: EdgeInsets.symmetric(vertical: 4),
          child: Text(
            p.replaceAll('**', ''),
            style: GoogleFonts.poppins(
              fontSize: 14,
              fontWeight: FontWeight.w600,
              color: Color(0xFF185FA5),
            ),
          ),
        );
      }
      return Padding(
        padding: EdgeInsets.only(bottom: 12),
        child: Text(
          p,
          style: GoogleFonts.poppins(
            fontSize: 13,
            color: Color(0xFF4B5563),
            height: 1.6,
          ),
        ),
      );
    }).toList();
  }

  Widget _buildBottomBar() {
    return Container(
      padding: EdgeInsets.only(left: 20, right: 20, top: 12, bottom: 16),
      decoration: BoxDecoration(
        color: Colors.white,
        boxShadow: [BoxShadow(color: Colors.black12, blurRadius: 8, offset: Offset(0, -2))],
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          if (!_hasScrolledToBottom)
            Text('Scroll to the bottom to accept',
              style: GoogleFonts.poppins(fontSize: 12, color: Colors.grey)),
          SizedBox(height: 8),
          SizedBox(
            width: double.infinity,
            child: ElevatedButton(
              onPressed: _hasScrolledToBottom ? _acceptTOS : null,
              child: _isAccepting
                  ? SizedBox(width: 20, height: 20,
                      child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white))
                  : Text('I Agree',
                      style: GoogleFonts.poppins(fontWeight: FontWeight.w600)),
            ),
          ),
        ],
      ),
    );
  }
}
