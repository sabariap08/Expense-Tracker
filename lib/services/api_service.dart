import 'dart:convert';
import 'package:http/http.dart' as http;
import '../config.dart';
import '../models/transaction.dart';

class ApiService {
  Future<Map<String, dynamic>> fetchDashboard() async {
    final response = await http.get(Uri.parse('${Config.apiBase}/dashboard'));
    if (response.statusCode != 200) throw Exception('Failed to load dashboard');
    return jsonDecode(response.body);
  }

  Future<Map<String, dynamic>> fetchTransactions({String? type, String? category}) async {
    final uri = Uri.parse('${Config.apiBase}/transactions').replace(queryParameters: {
      if (type != null && type != 'all') 'type': type,
      if (category != null && category.isNotEmpty) 'category': category,
    });
    final response = await http.get(uri);
    if (response.statusCode != 200) throw Exception('Failed to load transactions');
    return jsonDecode(response.body);
  }

  Future<Transaction> createTransaction(Map<String, dynamic> data) async {
    final response = await http.post(
      Uri.parse('${Config.apiBase}/transactions'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode(data),
    );
    if (response.statusCode != 201) throw Exception('Failed to create transaction');
    final body = jsonDecode(response.body);
    return Transaction.fromJson(body['transaction']);
  }

  Future<Transaction> updateTransaction(String id, Map<String, dynamic> data) async {
    final response = await http.put(
      Uri.parse('${Config.apiBase}/transactions/$id'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode(data),
    );
    if (response.statusCode != 200) throw Exception('Failed to update transaction');
    final body = jsonDecode(response.body);
    return Transaction.fromJson(body['transaction']);
  }

  Future<void> deleteTransaction(String id) async {
    final response = await http.delete(Uri.parse('${Config.apiBase}/transactions/$id'));
    if (response.statusCode != 200) throw Exception('Failed to delete transaction');
  }

  Future<List<String>> fetchCategories() async {
    final response = await http.get(Uri.parse('${Config.apiBase}/categories'));
    if (response.statusCode != 200) return [];
    final body = jsonDecode(response.body);
    final categories = List<String>.from(body['categories'] ?? []);
    return categories;
  }
}
