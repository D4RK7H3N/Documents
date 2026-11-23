import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:http/http.dart' as http;
import 'package:provider/provider.dart';
import 'package:web_socket_channel/web_socket_channel.dart';

import 'dart:io';

import 'package:image_picker/image_picker.dart';

import '../providers/auth_provider.dart';
import '../services/upload_service.dart';

class ChatScreen extends StatefulWidget {
  final int conversationId;
  final int tradeId;
  final String tradeTitle;

  const ChatScreen({
    super.key,
    required this.conversationId,
    required this.tradeId,
    required this.tradeTitle,
  });

  @override
  State<ChatScreen> createState() => _ChatScreenState();
}

class _ChatScreenState extends State<ChatScreen> {
  static const _apiUrl = 'http://10.0.2.2:8000/api';
  static const _wsUrl = 'ws://10.0.2.2:8000/ws';

  final _textController = TextEditingController();
  final _scrollController = ScrollController();
  late WebSocketChannel _channel;
  final List<Map<String, dynamic>> _messages = [];
  bool _isLoading = true;
  bool _isLocked = false;
  bool _isSending = false;

  @override
  void initState() {
    super.initState();
    _connectWebSocket();
    _loadHistory();
  }

  void _connectWebSocket() {
    final auth = context.read<AuthProvider>();
    final token = auth.accessToken;
    if (token == null) return;

    _channel = WebSocketChannel.connect(
      Uri.parse('$_wsUrl/chat/${widget.conversationId}/?token=$token'),
    );

    _channel.stream.listen(
      (data) {
        final msg = jsonDecode(data as String);
        if (msg['type'] == 'new_message') {
          setState(() => _messages.add(msg));
          _scrollDown();
        } else if (msg['type'] == 'error') {
          if (mounted) {
            ScaffoldMessenger.of(context).showSnackBar(
              SnackBar(content: Text(msg['message'])),
            );
          }
        }
      },
      onError: (err) {},
    );
  }

  Future<void> _loadHistory() async {
    final auth = context.read<AuthProvider>();
    final token = auth.accessToken;
    if (token == null) return;

    try {
      final uri = Uri.parse('$_apiUrl/conversations/${widget.conversationId}/');
      final response = await http.get(uri, headers: {
        'Authorization': 'Bearer $token',
      });
      if (response.statusCode == 200) {
        final body = jsonDecode(response.body);
        setState(() {
          _messages.clear();
          for (final m in body['messages']) {
            _messages.add({
              'id': m['id'],
              'sender_id': m['sender'],
              'sender_name': m['sender_name'],
              'text': m['text'],
              'image_url': m['image_url'] ?? '',
              'is_flagged': m['is_flagged'],
              'created_at': m['created_at'],
            });
          }
          _isLocked = body['conversation']['is_locked'] ?? false;
          _isLoading = false;
        });
        _scrollDown();
      }
    } catch (_) {
      setState(() => _isLoading = false);
    }
  }

  void _scrollDown() {
    Future.delayed(const Duration(milliseconds: 100), () {
      if (_scrollController.hasClients) {
        _scrollController.animateTo(
          _scrollController.position.maxScrollExtent,
          duration: const Duration(milliseconds: 200),
          curve: Curves.easeOut,
        );
      }
    });
  }

  void _sendMessage() async {
    final text = _textController.text.trim();
    if (text.isEmpty || _isSending || _isLocked) return;

    setState(() => _isSending = true);
    _textController.clear();

    _channel.sink.add(jsonEncode({
      'type': 'message',
      'text': text,
      'image_url': '',
    }));

    setState(() => _isSending = false);
  }

  Future<void> _sendImage() async {
    if (_isLocked) return;
    final picker = ImagePicker();
    final picked = await picker.pickImage(source: ImageSource.gallery);
    if (picked == null) return;
    try {
      final url = await UploadService.uploadImage(imageFile: File(picked.path));
      _channel.sink.add(jsonEncode({
        'type': 'message',
        'text': '',
        'image_url': url,
      }));
    } catch (_) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Failed to upload image')),
        );
      }
    }
  }

  void _reportMessage(int messageId) {
    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        title: Text('Report Message',
          style: GoogleFonts.poppins(fontWeight: FontWeight.w600)),
        content: TextField(
          decoration: InputDecoration(hintText: 'Why are you reporting this?'),
          maxLines: 3,
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx),
            child: Text('Cancel',
              style: GoogleFonts.poppins(color: Colors.grey)),
          ),
          TextButton(
            onPressed: () {
              Navigator.pop(ctx);
              ScaffoldMessenger.of(context).showSnackBar(
                SnackBar(content: Text('Message reported')),
              );
            },
            child: Text('Report',
              style: GoogleFonts.poppins(color: Colors.red)),
          ),
        ],
      ),
    );
  }

  @override
  void dispose() {
    _channel.sink.close();
    _textController.dispose();
    _scrollController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final auth = context.watch<AuthProvider>();
    final userId = auth.currentUser?['id'] as int? ?? 0;

    return Scaffold(
      backgroundColor: const Color(0xFFF4F8FD),
      appBar: AppBar(
        title: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(widget.tradeTitle,
              style: GoogleFonts.poppins(fontSize: 16, fontWeight: FontWeight.w600)),
            if (_isLocked)
              Text('Read-only — trade completed',
                style: GoogleFonts.poppins(fontSize: 11, color: Colors.orange)),
          ],
        ),
        actions: [
          IconButton(
            icon: Icon(Icons.flag_outlined, color: Colors.grey),
            onPressed: () {},
          ),
        ],
      ),
      body: Column(
        children: [
          Expanded(
            child: _isLoading
                ? Center(child: CircularProgressIndicator())
                : _messages.isEmpty
                    ? Center(child: Text('No messages yet',
                        style: GoogleFonts.poppins(color: Colors.grey)))
                    : ListView.builder(
                        controller: _scrollController,
                        padding: EdgeInsets.all(12),
                        itemCount: _messages.length,
                        itemBuilder: (_, i) {
                          final m = _messages[i];
                          final isMe = m['sender_id'] == userId;
                          return _MessageBubble(
                            message: m,
                            isMe: isMe,
                            onReport: () => _reportMessage(m['id']),
                          );
                        },
                      ),
          ),
          if (!_isLocked) _buildInputBar(),
        ],
      ),
    );
  }

  Widget _buildInputBar() {
    return Container(
      padding: EdgeInsets.only(left: 12, right: 8, top: 8, bottom: 8),
      decoration: BoxDecoration(
        color: Colors.white,
        boxShadow: [BoxShadow(color: Colors.black12, blurRadius: 8, offset: Offset(0, -2))],
      ),
      child: Row(
        children: [
          IconButton(
            icon: Icon(Icons.image_outlined, color: Color(0xFF185FA5)),
            onPressed: _sendImage,
          ),
          Expanded(
            child: TextField(
              controller: _textController,
              decoration: InputDecoration(
                hintText: 'Type a message...',
                filled: true,
                fillColor: Color(0xFFF4F8FD),
                border: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(24),
                  borderSide: BorderSide.none,
                ),
                contentPadding: EdgeInsets.symmetric(horizontal: 16, vertical: 12),
              ),
              textInputAction: TextInputAction.send,
              onSubmitted: (_) => _sendMessage(),
            ),
          ),
          SizedBox(width: 8),
          Container(
            decoration: BoxDecoration(
              gradient: LinearGradient(
                colors: [Color(0xFF185FA5), Color(0xFF534AB7)],
              ),
              shape: BoxShape.circle,
            ),
            child: IconButton(
              icon: Icon(Icons.send_rounded, color: Colors.white, size: 20),
              onPressed: _sendMessage,
            ),
          ),
        ],
      ),
    );
  }
}

class _MessageBubble extends StatelessWidget {
  final Map<String, dynamic> message;
  final bool isMe;
  final VoidCallback onReport;

  const _MessageBubble({
    required this.message,
    required this.isMe,
    required this.onReport,
  });

  @override
  Widget build(BuildContext context) {
    final text = message['text'] as String? ?? '';
    final imageUrl = message['image_url'] as String? ?? '';
    final isFlagged = message['is_flagged'] as bool? ?? false;

    return Padding(
      padding: EdgeInsets.only(bottom: 8),
      child: Column(
        crossAxisAlignment: isMe ? CrossAxisAlignment.end : CrossAxisAlignment.start,
        children: [
          if (!isMe)
            Padding(
              padding: EdgeInsets.only(left: 4, bottom: 2),
              child: Text(
                message['sender_name'] ?? '',
                style: GoogleFonts.poppins(
                  fontSize: 11,
                  fontWeight: FontWeight.w600,
                  color: Color(0xFF185FA5),
                ),
              ),
            ),
          GestureDetector(
            onLongPress: onReport,
            child: Container(
              constraints: BoxConstraints(maxWidth: MediaQuery.of(context).size.width * 0.75),
              padding: EdgeInsets.symmetric(horizontal: 14, vertical: 10),
              decoration: BoxDecoration(
                color: isMe
                    ? Color(0xFF185FA5)
                    : Colors.white,
                borderRadius: BorderRadius.circular(18).copyWith(
                  bottomRight: isMe ? Radius.zero : Radius.circular(18),
                  bottomLeft: isMe ? Radius.circular(18) : Radius.zero,
                ),
                boxShadow: [
                  BoxShadow(
                    color: Colors.black.withValues(alpha: 0.04),
                    blurRadius: 6,
                    offset: Offset(0, 2),
                  ),
                ],
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  if (imageUrl.isNotEmpty)
                    ClipRRect(
                      borderRadius: BorderRadius.circular(8),
                      child: Image.network(imageUrl,
                        height: 150, width: double.infinity, fit: BoxFit.cover),
                    ),
                  if (text.isNotEmpty) ...[
                    if (imageUrl.isNotEmpty) SizedBox(height: 6),
                    Text(
                      text,
                      style: GoogleFonts.poppins(
                        fontSize: 14,
                        color: isMe ? Colors.white : Color(0xFF1A1A2E),
                      ),
                    ),
                  ],
                  if (isFlagged)
                    Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Icon(Icons.warning_amber_rounded, size: 12,
                          color: isMe ? Colors.yellow.shade200 : Colors.orange),
                        SizedBox(width: 4),
                        Text('Flagged',
                          style: GoogleFonts.poppins(
                            fontSize: 9,
                            color: isMe ? Colors.yellow.shade200 : Colors.orange,
                          )),
                      ],
                    ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}
