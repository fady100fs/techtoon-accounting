using System.Windows;
using System.Windows.Controls;
using Techtoon.UI.ViewModels;

namespace Techtoon.UI.Views
{
    public partial class CashBoxesView : UserControl
    {
        public CashBoxesView()
        {
            InitializeComponent();
            SetArabicTexts();
            DataContext = new CashBoxesViewModel();
        }

        private void SetArabicTexts()
        {
            try { LblTitle.Text = "\u0627\u0644\u062E\u0632\u0627\u0626\u0646"; } catch { }
            try { BtnAdd.Content = "+ \u062E\u0632\u064A\u0646\u0629"; } catch { }
            try { BtnEdit.Content = "\u270E \u062A\u0639\u062F\u064A\u0644"; } catch { }
            try { BtnDelete.Content = "\uD83D\uDDD1"; } catch { }
            try { ColName.Header = "\u0627\u0644\u0627\u0633\u0645"; } catch { }
            try { ColCode.Header = "\u0627\u0644\u0643\u0648\u062F"; } catch { }
            try { ColType.Header = "\u0627\u0644\u0646\u0648\u0639"; } catch { }
            try { ColBalance.Header = "\u0631\u0635\u064A\u062F \u0627\u0641\u062A\u062A\u0627\u062D\u064A"; } catch { }
            try { ColStatus.Header = "\u0627\u0644\u062D\u0627\u0644\u0629"; } catch { }
        }

        private void UserControl_Loaded(object sender, RoutedEventArgs e) { }

        private void Dg_MouseDoubleClick(object sender, System.Windows.Input.MouseButtonEventArgs e)
        {
            if (DataContext is CashBoxesViewModel vm && vm.SelectedRow != null)
                vm.EditCommand.Execute(null);
        }
    }
}
