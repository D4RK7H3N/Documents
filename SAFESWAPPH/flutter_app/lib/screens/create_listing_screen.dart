import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:http/http.dart' as http;

import '../widgets/kyc_gate.dart';

class CreateListingScreen extends StatefulWidget {
  const CreateListingScreen({super.key});

  @override
  State<CreateListingScreen> createState() => _CreateListingScreenState();
}

class _CreateListingScreenState extends State<CreateListingScreen> {
  static const _baseUrl = 'http://10.0.2.2:8000/api';
  static const _storage = FlutterSecureStorage();

  final _titleController = TextEditingController();
  final _robloxUsernameController = TextEditingController();
  final _priceController = TextEditingController();
  final _descriptionController = TextEditingController();
  final _screenshotUrls = <String>[];

  bool _isLoading = false;

  @override
  void dispose() {
    _titleController.dispose();
    _robloxUsernameController.dispose();
    _priceController.dispose();
    _descriptionController.dispose();
    super.dispose();
  }

  Future<String?> _getToken() async {
    return await _storage.read(key: 'access_token');
  }

  Future<Map<String, String>> _authHeaders() async {
    final token = await _getToken();
    return {
      'Content-Type': 'application/json',
      if (token != null) 'Authorization': 'Bearer $token',
    };
  }

  Future<void> _submitListing() async {
    final title = _titleController.text.trim();
    final robloxUsername = _robloxUsernameController.text.trim();
    final priceText = _priceController.text.trim();

    if (title.isEmpty || robloxUsername.isEmpty || priceText.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Title, Roblox Username, and Price are required'),
          backgroundColor: Colors.red,
        ),
      );
      return;
    }

    final price = double.tryParse(priceText);
    if (price == null || price <= 0) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Please enter a valid price'),
          backgroundColor: Colors.red,
        ),
      );
      return;
    }

    setState(() => _isLoading = true);

    try {
      final body = jsonEncode({
        'title': title,
        'roblox_username': robloxUsername,
        'price': price,
        'description': _descriptionController.text.trim(),
        'screenshots': _screenshotUrls,
      });

      final response = await http
          .post(
            Uri.parse('$_baseUrl/listings/'),
            headers: await _authHeaders(),
            body: body,
          )
          .timeout(const Duration(seconds: 15));

      if (!mounted) return;

      if (response.statusCode == 201) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Listing created!'),
            backgroundColor: Colors.green,
          ),
        );
        Navigator.pop(context);
      } else {
        final data = jsonDecode(response.body) as Map<String, dynamic>;
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(data['error'] as String? ?? 'Failed to create listing'),
            backgroundColor: Colors.red,
          ),
        );
      }
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('Network error: $e'),
          backgroundColor: Colors.red,
        ),
      );
    } finally {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Create Listing')),
      body: KYCGate(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(24),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                'New Listing',
                style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                      fontWeight: FontWeight.bold,
                    ),
              ),
              const SizedBox(height: 24),
              TextField(
                controller: _titleController,
                decoration: const InputDecoration(
                  labelText: 'Title',
                  hintText: 'e.g. Level 500 account with limited items',
                ),
              ),
              const SizedBox(height: 16),
              TextField(
                controller: _robloxUsernameController,
                decoration: const InputDecoration(
                  labelText: 'Roblox Username',
                  prefixIcon: Icon(Icons.person),
                ),
              ),
              const SizedBox(height: 16),
              TextField(
                controller: _priceController,
                decoration: const InputDecoration(
                  labelText: 'Price (PHP)',
                  prefixText: '₱ ',
                ),
                keyboardType: TextInputType.number,
              ),
              const SizedBox(height: 16),
              TextField(
                controller: _descriptionController,
                maxLines: 4,
                decoration: const InputDecoration(
                  labelText: 'Description',
                  alignLabelWithHint: true,
                ),
              ),
              const SizedBox(height: 24),
              SizedBox(
                width: double.infinity,
                height: 50,
                child: ElevatedButton(
                  onPressed: _isLoading ? null : _submitListing,
                  child: _isLoading
                      ? const SizedBox(
                          width: 24,
                          height: 24,
                          child: CircularProgressIndicator(
                            strokeWidth: 2,
                            color: Colors.white,
                          ),
                        )
                      : const Text('Publish Listing'),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
