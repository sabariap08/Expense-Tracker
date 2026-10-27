import 'dart:convert';
import 'package:http/http.dart' as http;
import '../config.dart';

class AuthService {
  Future<bool> login(String username, String password) async {
    final response = await http.post(
      Uri.parse('${Config.apiBase}/auth/login'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({'username': username, 'password': password}),
    );
    return response.statusCode == 200;
  }

  Future<bool> checkStatus() async {
    final response = await http.get(Uri.parse('${Config.apiBase}/auth/status'));
    if (response.statusCode != 200) return false;
    final data = jsonDecode(response.body);
    return data['authenticated'] == true;
  }

  Future<void> logout() async {
    await http.post(Uri.parse('${Config.apiBase}/auth/logout'));
  }
}
