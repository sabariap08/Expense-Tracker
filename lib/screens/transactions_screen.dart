import 'package:flutter/material.dart';
import '../services/api_service.dart';
import '../models/transaction.dart';
import 'add_transaction_screen.dart';

class TransactionsScreen extends StatefulWidget {
  const TransactionsScreen({super.key});

  @override
  State<TransactionsScreen> createState() => _TransactionsScreenState();
}

class _TransactionsScreenState extends State<TransactionsScreen> {
  final _api = ApiService();
  List<Transaction> _transactions = [];
  bool _loading = true;
  String _type = 'all';

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() => _loading = true);
    try {
      final data = await _api.fetchTransactions(type: _type);
      final list = (data['transactions'] as List)
          .map((e) => Transaction.fromJson(e))
          .toList();
      setState(() => _transactions = list);
    } catch (e) {
      // ignore
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _delete(String id) async {
    try {
      await _api.deleteTransaction(id);
      _load();
    } catch (e) {
      // ignore
    }
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        Padding(
          padding: const EdgeInsets.all(8),
          child: SegmentedButton<String>(
            segments: const [
              ButtonSegment(value: 'all', label: Text('All')),
              ButtonSegment(value: 'credit', label: Text('Credit')),
              ButtonSegment(value: 'debit', label: Text('Debit')),
            ],
            selected: {_type},
            onSelectionChanged: (s) {
              setState(() => _type = s.first);
              _load();
            },
          ),
        ),
        Expanded(
          child: _loading
              ? const Center(child: CircularProgressIndicator())
              : RefreshIndicator(
                  onRefresh: _load,
                  child: ListView.builder(
                    itemCount: _transactions.length,
                    itemBuilder: (context, i) {
                      final t = _transactions[i];
                      return Dismissible(
                        key: Key(t.id),
                        background: Container(color: Colors.red, alignment: Alignment.centerRight, padding: const EdgeInsets.only(right: 16), child: const Icon(Icons.delete, color: Colors.white)),
                        direction: DismissDirection.endToStart,
                        onDismissed: (_) => _delete(t.id),
                        child: ListTile(
                          leading: CircleAvatar(
                            backgroundColor: t.type == 'credit' ? Colors.green[100] : Colors.red[100],
                            child: Icon(t.type == 'credit' ? Icons.arrow_downward : Icons.arrow_upward, color: t.type == 'credit' ? Colors.green : Colors.red),
                          ),
                          title: Text(t.title),
                          subtitle: Text('${t.date} • ${t.category}'),
                          trailing: Text('₹ ${t.amount}', style: TextStyle(color: t.type == 'credit' ? Colors.green : Colors.red, fontWeight: FontWeight.bold)),
                          onTap: () async {
                            final result = await Navigator.of(context).push(
                              MaterialPageRoute(builder: (_) => AddTransactionScreen(transaction: t)),
                            );
                            if (result == true) _load();
                          },
                        ),
                      );
                    },
                  ),
                ),
        ),
      ],
    );
  }
}
