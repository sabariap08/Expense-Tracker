class Transaction {
  final String id;
  final String type;
  final String typeLabel;
  final String title;
  final String description;
  final String amount;
  final String amountFormatted;
  final String date;
  final String category;
  final String paymentMethod;
  final String notes;

  Transaction({
    required this.id,
    required this.type,
    required this.typeLabel,
    required this.title,
    required this.description,
    required this.amount,
    required this.amountFormatted,
    required this.date,
    required this.category,
    required this.paymentMethod,
    required this.notes,
  });

  factory Transaction.fromJson(Map<String, dynamic> json) {
    return Transaction(
      id: json['_id'] ?? '',
      type: json['type'] ?? '',
      typeLabel: json['type_label'] ?? '',
      title: json['title'] ?? '',
      description: json['description'] ?? '',
      amount: json['amount'] ?? '0.00',
      amountFormatted: json['amount_formatted'] ?? '0.00',
      date: json['date'] ?? '',
      category: json['category'] ?? '',
      paymentMethod: json['payment_method'] ?? '',
      notes: json['notes'] ?? '',
    );
  }
}
