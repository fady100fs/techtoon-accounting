using System.Windows;
using System.Windows.Input;
using Techtoon.UI.ViewModels;

namespace Techtoon.UI
{
    public partial class MainWindow : Window
    {
        public MainWindow()
        {
            InitializeComponent();
            PasswordBox.KeyDown += PasswordBox_KeyDown;
        }

        private void PasswordBox_KeyDown(object sender, KeyEventArgs e)
        {
            if (e.Key == Key.Enter)
            {
                if (DataContext is MainViewModel vm)
                {
                    vm.Password = PasswordBox.Password;
                    vm.LoginCommand.Execute(null);
                }
            }
        }
    }
}