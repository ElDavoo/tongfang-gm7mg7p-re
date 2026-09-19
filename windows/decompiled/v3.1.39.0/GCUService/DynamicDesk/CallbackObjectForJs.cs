using System.Windows;

namespace DynamicDesk;

public class CallbackObjectForJs
{
	public string name = "";

	public void showTest(string msg)
	{
		MessageBox.Show(msg);
		MessageBox.Show(name);
	}
}
