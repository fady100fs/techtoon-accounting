using System;
using System.Collections.ObjectModel;
using System.Linq;
using System.Windows.Input;
using CommunityToolkit.Mvvm.Input;
using Npgsql;

namespace Techtoon.UI.ViewModels
{
    public class CashBoxRow : ViewModelBase
    {
        public int Id { get; set; }
        public string Name { get; set; }
        public string Code { get; set; }
        public string Type { get; set; }
        public decimal OpeningBalance { get; set; }
        public bool IsActive { get; set; }
        private bool _isSelected;
        public bool IsSelected { get => _isSelected; set => SetProperty(ref _isSelected, value); }
        public string TypeDisplay => Type switch { "bank" => "\u0628\u0646\u0643", "wallet" => "\u0645\u062D\u0641\u0638\u0629", _ => "\u0646\u0642\u062F\u064A" };
        public string OpeningDisplay => OpeningBalance.ToString("N2");
        public string StatusDisplay => IsActive ? "\u0646\u0634\u0637" : "\u063A\u064A\u0631 \u0646\u0634\u0637";
    }

    public class CashBoxesViewModel : ViewModelBase
    {
        public ObservableCollection<CashBoxRow> CashBoxes { get; } = new();
        private string _statusMessage = "";
        public string StatusMessage { get => _statusMessage; set => SetProperty(ref _statusMessage, value); }
        private CashBoxRow _selectedRow;
        public CashBoxRow SelectedRow { get => _selectedRow; set => SetProperty(ref _selectedRow, value); }

        public ICommand RefreshCommand { get; }
        public ICommand AddCommand { get; }
        public ICommand EditCommand { get; }
        public ICommand DeleteCommand { get; }

        public CashBoxesViewModel()
        {
            RefreshCommand = new RelayCommand(LoadCashBoxes);
            AddCommand = new RelayCommand(AddNew);
            EditCommand = new RelayCommand(EditSelected, () => SelectedRow != null);
            DeleteCommand = new RelayCommand(DeleteSelected, () => SelectedRow != null);
            LoadCashBoxes();
        }

        public static string GetCS() => "Host=ep-bitter-night-za726w59-pooler.c-2.eu-west-2.aws.neon.tech;Port=5432;Username=neondb_owner;Password=npg_K9nHVkY5OjRC;Database=neondb;SSL Mode=Require;Trust Server Certificate=true";

        public void LoadCashBoxes()
        {
            CashBoxes.Clear();
            try
            {
                using var conn = new NpgsqlConnection(GetCS());
                conn.Open();
                using var cmd = new NpgsqlCommand("SELECT id, name, code, COALESCE(type,'cash'), COALESCE(opening_balance,0), COALESCE(is_active,TRUE) FROM cash_boxes ORDER BY name", conn);
                using var r = cmd.ExecuteReader();
                while (r.Read())
                    CashBoxes.Add(new CashBoxRow { Id = r.GetInt32(0), Name = r.GetString(1), Code = r.IsDBNull(2) ? "" : r.GetString(2), Type = r.IsDBNull(3) ? "cash" : r.GetString(3), OpeningBalance = r.IsDBNull(4) ? 0 : (decimal)r.GetDouble(4), IsActive = r.IsDBNull(5) ? true : r.GetBoolean(5) });
                StatusMessage = "\u062A\u0645 \u062A\u062D\u0645\u064A\u0644 " + CashBoxes.Count + " \u062E\u0632\u064A\u0646\u0629";
            }
            catch (Exception ex) { StatusMessage = "\u062E\u0637\u0623: " + ex.Message; }
        }

        private void AddNew() { ShowEditWindow(null); }
        private void EditSelected() { if (SelectedRow != null) ShowEditWindow(SelectedRow); }

        private void ShowEditWindow(CashBoxRow row)
        {
            var win = new System.Windows.Window
            {
                Title = row == null ? "\u0625\u0636\u0627\u0641\u0629 \u062E\u0632\u064A\u0646\u0629" : "\u062A\u0639\u062F\u064A\u0644 \u062E\u0632\u064A\u0646\u0629",
                Width = 400, Height = 350, WindowStartupLocation = System.Windows.WindowStartupLocation.CenterScreen,
                FlowDirection = System.Windows.FlowDirection.RightToLeft, FontFamily = new System.Windows.Media.FontFamily("Tahoma"),
                Background = new System.Windows.Media.SolidColorBrush(System.Windows.Media.Color.FromRgb(245, 247, 250))
            };

            var panel = new System.Windows.Controls.StackPanel { Margin = new System.Windows.Thickness(20) };
            var txtName = new System.Windows.Controls.TextBox { Padding = new System.Windows.Thickness(6, 4, 6, 4), Margin = new System.Windows.Thickness(0, 0, 0, 10) };
            var txtCode = new System.Windows.Controls.TextBox { Padding = new System.Windows.Thickness(6, 4, 6, 4), Margin = new System.Windows.Thickness(0, 0, 0, 10) };
            var cmbType = new System.Windows.Controls.ComboBox { Padding = new System.Windows.Thickness(6, 4, 6, 4), Margin = new System.Windows.Thickness(0, 0, 0, 10) };
            cmbType.Items.Add(new System.Windows.Controls.ComboBoxItem { Content = "\u0646\u0642\u062F\u064A", Tag = "cash" });
            cmbType.Items.Add(new System.Windows.Controls.ComboBoxItem { Content = "\u0628\u0646\u0643", Tag = "bank" });
            cmbType.Items.Add(new System.Windows.Controls.ComboBoxItem { Content = "\u0645\u062D\u0641\u0638\u0629 \u0627\u0644\u0643\u062A\u0631\u0648\u0646\u064A\u0629", Tag = "wallet" });
            cmbType.SelectedIndex = 0;
            var txtBalance = new System.Windows.Controls.TextBox { Padding = new System.Windows.Thickness(6, 4, 6, 4), Margin = new System.Windows.Thickness(0, 0, 0, 10), TextAlignment = System.Windows.TextAlignment.Right };
            var chkActive = new System.Windows.Controls.CheckBox { Content = "\u0646\u0634\u0637", IsChecked = true, Margin = new System.Windows.Thickness(0, 0, 0, 15) };

            if (row != null)
            {
                txtName.Text = row.Name;
                txtCode.Text = row.Code;
                txtBalance.Text = row.OpeningBalance.ToString("N2");
                chkActive.IsChecked = row.IsActive;
                for (int i = 0; i < cmbType.Items.Count; i++)
                    if ((cmbType.Items[i] as System.Windows.Controls.ComboBoxItem).Tag?.ToString() == row.Type) { cmbType.SelectedIndex = i; break; }
            }

            panel.Children.Add(new System.Windows.Controls.TextBlock { Text = "\u0627\u0644\u0627\u0633\u0645:", Margin = new System.Windows.Thickness(0, 0, 0, 3) });
            panel.Children.Add(txtName);
            panel.Children.Add(new System.Windows.Controls.TextBlock { Text = "\u0627\u0644\u0643\u0648\u062F:", Margin = new System.Windows.Thickness(0, 0, 0, 3) });
            panel.Children.Add(txtCode);
            panel.Children.Add(new System.Windows.Controls.TextBlock { Text = "\u0627\u0644\u0646\u0648\u0639:", Margin = new System.Windows.Thickness(0, 0, 0, 3) });
            panel.Children.Add(cmbType);
            panel.Children.Add(new System.Windows.Controls.TextBlock { Text = "\u0627\u0644\u0631\u0635\u064A\u062F \u0627\u0644\u0627\u0641\u062A\u062A\u0627\u062D\u064A:", Margin = new System.Windows.Thickness(0, 0, 0, 3) });
            panel.Children.Add(txtBalance);
            panel.Children.Add(chkActive);

            var btnOk = new System.Windows.Controls.Button { Content = "\u062D\u0641\u0638", Background = new System.Windows.Media.SolidColorBrush(System.Windows.Media.Color.FromRgb(0, 137, 123)), Foreground = System.Windows.Media.Brushes.White, FontWeight = System.Windows.FontWeights.Bold, Padding = new System.Windows.Thickness(30, 8, 30, 8), BorderThickness = new System.Windows.Thickness(0), HorizontalAlignment = System.Windows.HorizontalAlignment.Center };
            panel.Children.Add(btnOk);
            win.Content = panel;

            btnOk.Click += (s, e) =>
            {
                try
                {
                    if (string.IsNullOrWhiteSpace(txtName.Text)) { System.Windows.MessageBox.Show("\u0623\u062F\u062E\u0644 \u0627\u0644\u0627\u0633\u0645"); return; }
                    decimal bal = 0; decimal.TryParse(txtBalance.Text, out bal);
                    string type = (cmbType.SelectedItem as System.Windows.Controls.ComboBoxItem)?.Tag?.ToString() ?? "cash";

                    using var conn = new NpgsqlConnection(GetCS());
                    conn.Open();
                    if (row == null)
                    {
                        using var cmd = new NpgsqlCommand("INSERT INTO cash_boxes (name, code, type, opening_balance, is_active, created_at) VALUES (@n, @c, @t, @b, @a, NOW())", conn);
                        cmd.Parameters.AddWithValue("n", txtName.Text.Trim());
                        cmd.Parameters.AddWithValue("c", txtCode.Text.Trim());
                        cmd.Parameters.AddWithValue("t", type);
                        cmd.Parameters.AddWithValue("b", (double)bal);
                        cmd.Parameters.AddWithValue("a", chkActive.IsChecked ?? true);
                        cmd.ExecuteNonQuery();
                    }
                    else
                    {
                        using var cmd = new NpgsqlCommand("UPDATE cash_boxes SET name=@n, code=@c, type=@t, opening_balance=@b, is_active=@a WHERE id=@id", conn);
                        cmd.Parameters.AddWithValue("n", txtName.Text.Trim());
                        cmd.Parameters.AddWithValue("c", txtCode.Text.Trim());
                        cmd.Parameters.AddWithValue("t", type);
                        cmd.Parameters.AddWithValue("b", (double)bal);
                        cmd.Parameters.AddWithValue("a", chkActive.IsChecked ?? true);
                        cmd.Parameters.AddWithValue("id", row.Id);
                        cmd.ExecuteNonQuery();
                    }
                    win.Close();
                    LoadCashBoxes();
                }
                catch (Exception ex) { System.Windows.MessageBox.Show("\u062E\u0637\u0623: " + ex.Message); }
            };

            win.ShowDialog();
        }

        private void DeleteSelected()
        {
            if (SelectedRow == null) return;
            if (System.Windows.MessageBox.Show("\u062D\u0630\u0641 \u0627\u0644\u062E\u0632\u064A\u0646\u0629\u061F", "\u062A\u0623\u0643\u064A\u062F", System.Windows.MessageBoxButton.YesNo, System.Windows.MessageBoxImage.Warning) != System.Windows.MessageBoxResult.Yes) return;
            try { using var conn = new NpgsqlConnection(GetCS()); conn.Open(); using var cmd = new NpgsqlCommand("DELETE FROM cash_boxes WHERE id=@id", conn); cmd.Parameters.AddWithValue("id", SelectedRow.Id); cmd.ExecuteNonQuery(); LoadCashBoxes(); }
            catch (Exception ex) { StatusMessage = "\u062E\u0637\u0623: " + ex.Message; }
        }
    }
}
