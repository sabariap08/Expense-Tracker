import 'package:flutter/material.dart';
import '../services/api_service.dart';
import '../models/transaction.dart';

class AddTransactionScreen extends StatefulWidget {
  final Transaction? transaction;
  const AddTransactionScreen({super.key, this.transaction});

  @override
  State<AddTransactionScreen> createState() => _AddTransactionScreenState();
}

class _AddTransactionScreenState extends State<AddTransactionScreen> {
  final _formKey = GlobalKey<FormState>();
  final _api = ApiService();
  String _type = 'debit';
  final _title = TextEditingController();
  final _description = TextEditingController();
  final _amount = TextEditingController();
  final _date = TextEditingController();
  final _category = TextEditingController();
  final _paymentMethod = TextEditingController();
  final _notes = TextEditingController();
  bool _loading = false;
  List<String> _categories = [];

  @override
  void initState() {
    super.initState();
    _loadCategories();
    if (widget.transaction != null) {
      final t = widget.transaction!;
      _type = t.type;
      _title.text = t.title;
      _description.text = t.description;
      _amount.text = t.amount;
      _date.text = t.date;
      _category.text = t.category;
      _paymentMethod.text = t.paymentMethod;
      _notes.text = t.notes;
    } else {
      _date.text = DateTime.now().toString().substring(0, 10);
    }
  }

  Future<void> _loadCategories() async {
    final cats = await _api.fetchCategories();
    setState(() => _categories = cats);
  }

  Future<void> _save() async {
    if (!_formKey.currentState!.validate()) return;
    setState(() => _loading = true);
    final data = {
      'type': _type,
      'title': _title.text,
      'description': _description.text,
      'amount': _amount.text,
      'date': _date.text,
      'category': _category.text,
      'payment_method': _paymentMethod.text,
      'notes': _notes.text,
    };
    try {
      if (widget.transaction == null) {
        await _api.createTransaction(data);
      } else {
        await _api.updateTransaction(widget.transaction!.id, data);
      }
      if (mounted) Navigator.of(context).pop(true);
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Failed to save')));
      }
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text(widget.transaction == null ? 'Add Transaction' : 'Edit Transaction')),
      body: Form(
        key: _formKey,
        child: ListView(
          padding: const EdgeInsets.all(16),
          children: [
            SegmentedButton<String>(
              segments: const [
                ButtonSegment(value: 'debit', label: Text('Debit')),
                ButtonSegment(value: 'credit', label: Text('Credit')),
              ],
              selected: {_type},
              onSelectionChanged: (s) => setState(() => _type = s.first),
            ),
            const SizedBox(height: 16),
            TextFormField(controller: _title, decoration: const InputDecoration(labelText: 'Title *'), validator: (v) => v!.isEmpty ? 'Required' : null),
            const SizedBox(height: 12),
            TextFormField(controller: _amount, decoration: const InputDecoration(labelText: 'Amount *'), keyboardType: const TextInputType.numberWithOptions(decimal: true), validator: (v) => v!.isEmpty ? 'Required' : null),
            const SizedBox(height: 12),
            TextFormField(controller: _date, decoration: const InputDecoration(labelText: 'Date *'), validator: (v) => v!.isEmpty ? 'Required' : null),
            const SizedBox(height: 12),
            DropdownButtonFormField<String>(
              value: _category.text.isEmpty ? null : _category.text,
              decoration: const InputDecoration(labelText: 'Category'),
              items: _categories.map((c) => DropdownMenuItem(value: c, child: Text(c))).toList(),
              onChanged: (v) => setState(() => _category.text = v ?? ''),
            ),
            const SizedBox(height: 12),
            TextFormField(controller: _description, decoration: const InputDecoration(labelText: 'Description')),
            const SizedBox(height: 12),
            TextFormField(controller: _paymentMethod, decoration: const InputDecoration(labelText: 'Payment Method')),
            const SizedBox(height: 12),
            TextFormField(controller: _notes, decoration: const InputDecoration(labelText: 'Notes'), maxLines: 3),
            const SizedBox(height: 24),
            FilledButton(
              onPressed: _loading ? null : _save,
              child: _loading ? const CircularProgressIndicator() : const Text('Save'),
            ),
          ],
        ),
      ),
    );
  }
}
