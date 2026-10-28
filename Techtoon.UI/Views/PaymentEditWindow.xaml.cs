using System;
using System.Collections.ObjectModel;
using System.Windows;
using Npgsql;

namespace Techtoon.UI.Views
{
    public partial class PaymentEditWindow : Window
    {
        private readonly string _connectionString =
            "Host=ep-bitter-night-za726w59-pooler.c-2.eu-west-2.aws.neon.tech;Port=5432;" +
            "Username=neondb_owner;Password=npg_K9nHVkY5OjRC;Database=neondb;" +
            "SSL Mode=Require;Trust Server Certificate=true";

        private int _paymentId;
        private bool _isEditMode;
        private bool _isReceipt = true;

        public bool Saved { get; private set; }
        public int SavedPaymentId { get; private set; }

        public ObservableCollection<PartyItem> Parties { get; }
        public ObservableCollection<InvoiceItem> Invoices { get; }
        public ObservableCollection<CashBoxItem> CashBoxes { get; }
        public ObservableCollection<string> Methods { get; }

        public PaymentEditWindow()
        {
            InitializeComponent();
            Parties = new ObservableCollection<PartyItem>();
            Invoices = new ObservableCollection<InvoiceItem>();
            CashBoxes = new ObservableCollection<CashBoxItem>();
            Methods = new ObservableCollection<string>();
            Methods.Add("نقدي");
            Methods.Add("بطاقة");
            Methods.Add("تحويل");
            DataContext = this;

            // ربط ComboBoxات بالقوائم
            if (cmbMethod != null)
            {
                cmbMethod.ItemsSource = Methods;
                cmbMethod.SelectedIndex = 0;
            }
            if (cmbParty != null) cmbParty.ItemsSource = Parties;
            if (cmbInvoice != null) cmbInvoice.ItemsSource = Invoices;
            if (cmbCashBox != null) cmbCashBox.ItemsSource = CashBoxes;

            if (dpDate != null) dpDate.SelectedDate = DateTime.Today;

            // إضافة "بدون فاتورة" افتراضياً
            Invoices.Add(new InvoiceItem { Id = 0, Number = "بدون فاتورة" });
            if (cmbInvoice != null) cmbInvoice.SelectedIndex = 0;

            LoadLookups();
        }

        public void SetMode(bool isReceipt)
        {
            _isReceipt = isReceipt;
            Title = isReceipt ? "سند قبض" : "سند صرف";
            if (lblParty != null)
            {
                lblParty.Text = isReceipt ? "العميل" : "المورد";
            }
        }

        public void LoadForEdit(int paymentId)
        {
            _paymentId = paymentId;
            _isEditMode = true;
            Title = "تعديل السند";
            NpgsqlConnection conn = null;
            try
            {
                conn = new NpgsqlConnection(_connectionString);
                conn.Open();
                using (var cmd = new NpgsqlCommand(
                    "SELECT party_id, invoice_id, amount, date, cash_box_id, " +
                    "payment_method, reference_number, notes, payment_type " +
                    "FROM payments WHERE id = @id", conn))
                {
                    cmd.Parameters.AddWithValue("@id", paymentId);
                    using (var reader = cmd.ExecuteReader())
                    {
                        if (reader.Read())
                        {
                            _isReceipt = reader.GetString(8) == "receipt";
                            int pid = reader.IsDBNull(0) ? 0 : reader.GetInt32(0);
                            int iid = reader.IsDBNull(1) ? 0 : reader.GetInt32(1);
                            if (cmbParty != null) cmbParty.SelectedValue = pid;
                            if (txtAmount != null) txtAmount.Text = reader.IsDBNull(2) ? "" : reader.GetDouble(2).ToString("0.00");
                            if (dpDate != null) dpDate.SelectedDate = reader.IsDBNull(3) ? (DateTime?)DateTime.Today : reader.GetDateTime(3);
                            if (cmbCashBox != null) cmbCashBox.SelectedValue = reader.IsDBNull(4) ? 0 : reader.GetInt32(4);
                            if (cmbMethod != null) cmbMethod.SelectedItem = reader.IsDBNull(5) ? null : reader.GetString(5);
                            if (txtRef != null) txtRef.Text = reader.IsDBNull(6) ? "" : reader.GetString(6);
                            if (txtNotes != null) txtNotes.Text = reader.IsDBNull(7) ? "" : reader.GetString(7);
                            LoadInvoices(pid);
                            if (iid > 0 && cmbInvoice != null) cmbInvoice.SelectedValue = iid;
                        }
                    }
                }
            }
            catch (Exception ex)
            {
                MessageBox.Show("خطأ: " + ex.Message);
            }
            finally
            {
                if (conn != null) conn.Close();
            }
        }

        private void LoadLookups()
        {
            LoadParties();
            LoadCashBoxes();
        }

        private void LoadParties()
        {
            Parties.Clear();
            NpgsqlConnection conn = null;
            try
            {
                conn = new NpgsqlConnection(_connectionString);
                conn.Open();
                // استعلام آمن: نتحقق من وجود is_active قبل استخدامه
                string sql = "SELECT id, name, type FROM parties ";
                // تحقق من عمود is_active
                bool hasIsActive = false;
                using (var chk = new NpgsqlCommand(
                    "SELECT column_name FROM information_schema.columns WHERE table_name='parties' AND column_name='is_active'", conn))
                using (var rdr = chk.ExecuteReader())
                {
                    hasIsActive = rdr.Read();
                }
                if (hasIsActive) sql += "WHERE is_active = TRUE ";
                sql += "ORDER BY name";

                using (var cmd = new NpgsqlCommand(sql, conn))
                using (var reader = cmd.ExecuteReader())
                {
                    while (reader.Read())
                    {
                        Parties.Add(new PartyItem
                        {
                            Id = reader.GetInt32(0),
                            Name = reader.GetString(1),
                            Type = reader.IsDBNull(2) ? "" : reader.GetString(2)
                        });
                    }
                }
            }
            catch (Exception ex)
            {
                MessageBox.Show("خطأ تحميل الأطراف: " + ex.Message);
            }
            finally
            {
                if (conn != null) conn.Close();
            }
        }

        private void LoadInvoices(int partyId)
        {
            Invoices.Clear();
            Invoices.Add(new InvoiceItem { Id = 0, Number = "بدون فاتورة" });
            if (partyId <= 0)
            {
                if (cmbInvoice != null) cmbInvoice.SelectedIndex = 0;
                return;
            }
            NpgsqlConnection conn = null;
            try
            {
                conn = new NpgsqlConnection(_connectionString);
                conn.Open();
                using (var cmd = new NpgsqlCommand(
                    "SELECT id, invoice_number, total, paid_amount " +
                    "FROM invoices WHERE party_id = @pid AND status <> 'cancelled' " +
                    "ORDER BY date DESC", conn))
                {
                    cmd.Parameters.AddWithValue("@pid", partyId);
                    using (var reader = cmd.ExecuteReader())
                    {
                        while (reader.Read())
                        {
                            decimal total = reader.IsDBNull(2) ? 0m : reader.GetDecimal(2);
                            decimal paid = reader.IsDBNull(3) ? 0m : reader.GetDecimal(3);
                            Invoices.Add(new InvoiceItem
                            {
                                Id = reader.GetInt32(0),
                                Number = reader.GetString(1) + " (متبقي: " + (total - paid).ToString("0.00") + ")",
                                Total = total,
                                Paid = paid
                            });
                        }
                    }
                }
            }
            catch (Exception ex)
            {
                MessageBox.Show("خطأ تحميل الفواتير: " + ex.Message);
            }
            finally
            {
                if (conn != null) conn.Close();
            }
            if (cmbInvoice != null && cmbInvoice.Items.Count > 0)
                cmbInvoice.SelectedIndex = 0;
        }

        private void LoadCashBoxes()
        {
            CashBoxes.Clear();
            NpgsqlConnection conn = null;
            try
            {
                conn = new NpgsqlConnection(_connectionString);
                conn.Open();
                string sql = "SELECT id, name FROM cash_boxes ";
                bool hasIsActive = false;
                using (var chk = new NpgsqlCommand(
                    "SELECT column_name FROM information_schema.columns WHERE table_name='cash_boxes' AND column_name='is_active'", conn))
                using (var rdr = chk.ExecuteReader())
                {
                    hasIsActive = rdr.Read();
                }
                if (hasIsActive) sql += "WHERE is_active = TRUE ";
                sql += "ORDER BY name";

                using (var cmd = new NpgsqlCommand(sql, conn))
                using (var reader = cmd.ExecuteReader())
                {
                    while (reader.Read())
                    {
                        CashBoxes.Add(new CashBoxItem
                        {
                            Id = reader.GetInt32(0),
                            Name = reader.GetString(1)
                        });
                    }
                }
            }
            catch (Exception ex)
            {
                MessageBox.Show("خطأ تحميل الصناديق: " + ex.Message);
            }
            finally
            {
                if (conn != null) conn.Close();
            }
            if (cmbCashBox != null && cmbCashBox.Items.Count > 0)
                cmbCashBox.SelectedIndex = 0;
        }

        private void CmbParty_SelectionChanged(object sender, System.Windows.Controls.SelectionChangedEventArgs e)
        {
            if (cmbParty == null) return;
            int? pid = cmbParty.SelectedValue as int?;
            if (pid.HasValue && pid.Value > 0)
            {
                LoadInvoices(pid.Value);
            }
        }

        private bool ValidateForm()
        {
            int? pid = cmbParty.SelectedValue as int?;
            if (!pid.HasValue || pid.Value <= 0)
            {
                MessageBox.Show("اختر الطرف");
                return false;
            }
            if (!decimal.TryParse(txtAmount.Text, out decimal amount) || amount <= 0)
            {
                MessageBox.Show("المبلغ غير صحيح");
                return false;
            }
            int? cbid = cmbCashBox.SelectedValue as int?;
            if (!cbid.HasValue || cbid.Value <= 0)
            {
                MessageBox.Show("اختر الصندوق");
                return false;
            }
            return true;
        }

        private void BtnSave_Click(object sender, RoutedEventArgs e)
        {
            if (!ValidateForm()) return;
            int partyId = (cmbParty.SelectedValue as int?) ?? 0;
            int invoiceId = (cmbInvoice.SelectedValue as int?) ?? 0;
            double amount = (double)decimal.Parse(txtAmount.Text);
            DateTime date = dpDate.SelectedDate ?? DateTime.Today;
            int cashBoxId = (cmbCashBox.SelectedValue as int?) ?? 0;
            string method = cmbMethod.SelectedItem == null ? "نقدي" : cmbMethod.SelectedItem.ToString();
            string reference = txtRef.Text.Trim();
            string notes = txtNotes.Text.Trim();
            string pType = _isReceipt ? "receipt" : "payment";

            NpgsqlConnection conn = null;
            try
            {
                conn = new NpgsqlConnection(_connectionString);
                conn.Open();
                using (var tx = conn.BeginTransaction())
                {
                    if (_isEditMode)
                    {
                        using (var cmd = new NpgsqlCommand(
                            "UPDATE payments SET party_id=@pid, invoice_id=@iid, amount=@amt, " +
                            "date=@dt, cash_box_id=@cb, payment_method=@m, " +
                            "reference_number=@ref, notes=@n, payment_type=@t WHERE id=@id", conn, tx))
                        {
                            AddParams(cmd, partyId, invoiceId, amount, date, cashBoxId, method, reference, notes, pType);
                            cmd.Parameters.AddWithValue("@id", _paymentId);
                            cmd.ExecuteNonQuery();
                        }
                        SavedPaymentId = _paymentId;
                    }
                    else
                    {
                        using (var cmd = new NpgsqlCommand(
                            "INSERT INTO payments (party_id, invoice_id, amount, date, " +
                            "cash_box_id, payment_method, reference_number, notes, payment_type, currency_id) " +
                            "VALUES (@pid, @iid, @amt, @dt, @cb, @m, @ref, @n, @t, 1) RETURNING id", conn, tx))
                        {
                            AddParams(cmd, partyId, invoiceId, amount, date, cashBoxId, method, reference, notes, pType);
                            var result = cmd.ExecuteScalar();
                            SavedPaymentId = Convert.ToInt32(result);
                            _paymentId = SavedPaymentId;
                        }
                    }
                    if (invoiceId > 0)
                    {
                        using (var cmd = new NpgsqlCommand(
                            "UPDATE invoices SET paid_amount = COALESCE(" +
                            "(SELECT SUM(amount) FROM payments WHERE invoice_id=@iid AND payment_type='receipt'), 0) " +
                            "WHERE id=@iid", conn, tx))
                        {
                            cmd.Parameters.AddWithValue("@iid", invoiceId);
                            cmd.ExecuteNonQuery();
                        }
                    }
                    tx.Commit();
                }
                Saved = true;
                MessageBox.Show("تم الحفظ بنجاح");
                DialogResult = true;
                Close();
            }
            catch (Exception ex)
            {
                MessageBox.Show("خطأ: " + ex.Message);
            }
            finally
            {
                if (conn != null) conn.Close();
            }
        }

        private static void AddParams(NpgsqlCommand cmd,
            int partyId, int invoiceId, double amount, DateTime date,
            int cashBoxId, string method, string reference, string notes, string pType)
        {
            cmd.Parameters.AddWithValue("@pid", partyId);
            cmd.Parameters.AddWithValue("@iid", invoiceId > 0 ? (object)invoiceId : DBNull.Value);
            cmd.Parameters.AddWithValue("@amt", amount);
            cmd.Parameters.AddWithValue("@dt", date);
            cmd.Parameters.AddWithValue("@cb", cashBoxId);
            cmd.Parameters.AddWithValue("@m", method);
            cmd.Parameters.AddWithValue("@ref", string.IsNullOrEmpty(reference) ? (object)DBNull.Value : reference);
            cmd.Parameters.AddWithValue("@n", string.IsNullOrEmpty(notes) ? (object)DBNull.Value : notes);
            cmd.Parameters.AddWithValue("@t", pType);
        }

        private void BtnCancel_Click(object sender, RoutedEventArgs e)
        {
            DialogResult = false;
            Close();
        }
    }

    public class PartyItem
    {
        public int Id { get; set; }
        public string Name { get; set; }
        public string Type { get; set; }
    }

    public class InvoiceItem
    {
        public int Id { get; set; }
        public string Number { get; set; }
        public decimal Total { get; set; }
        public decimal Paid { get; set; }
    }

    public class CashBoxItem
    {
        public int Id { get; set; }
        public string Name { get; set; }
    }
}
