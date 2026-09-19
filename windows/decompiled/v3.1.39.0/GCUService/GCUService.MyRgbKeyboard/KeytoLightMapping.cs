using System.Collections.Generic;
using System.Linq;
using System.Runtime.InteropServices;
using System.Text;
using System.Windows.Forms;
using LightingModel;

namespace GCUService.MyRgbKeyboard;

internal class KeytoLightMapping
{
	private RGBKB_Type KeyboardType;

	private Dictionary<Keys, string> keyMapping = new Dictionary<Keys, string>();

	[DllImport("user32", SetLastError = true)]
	private static extern int GetKeyNameText(int lParam, StringBuilder lpString, int cchSize);

	public KeytoLightMapping()
	{
		List<Keys> keys = EnumHelper.ToList<Keys>();
		Create101KeyMapping(keys);
	}

	public string ReturnLightNumber(Keys key)
	{
		if (!keyMapping.Keys.Contains(key))
		{
			return null;
		}
		return keyMapping[key];
	}

	private void Create101KeyMapping(List<Keys> keys)
	{
		int num = 0;
		keyMapping.Add(Keys.Escape, "0");
		num = 1;
		foreach (Keys item in keys.Skip(107).Take(12))
		{
			keyMapping.Add(item, num.ToString());
			num++;
		}
		keyMapping.Add(Keys.Snapshot, "13");
		keyMapping.Add(Keys.Pause, "14");
		keyMapping.Add(Keys.Delete, "15");
		keyMapping.Add(Keys.End, "16");
		num = 21;
		keyMapping.Add(Keys.Oemtilde, num.ToString());
		num++;
		foreach (Keys item2 in keys.Skip(52).Take(9))
		{
			keyMapping.Add(item2, num.ToString());
			num++;
		}
		keyMapping.Add(Keys.D0, num.ToString());
		num++;
		keyMapping.Add(Keys.OemMinus, num.ToString());
		num++;
		keyMapping.Add(Keys.Oemplus, num.ToString());
		num++;
		keyMapping.Add(Keys.Back, num.ToString());
		num = 42;
		keyMapping.Add(Keys.Tab, num.ToString());
		num++;
		keyMapping.Add(Keys.Q, num.ToString());
		num++;
		keyMapping.Add(Keys.W, num.ToString());
		num++;
		keyMapping.Add(Keys.E, num.ToString());
		num++;
		keyMapping.Add(Keys.R, num.ToString());
		num++;
		keyMapping.Add(Keys.T, num.ToString());
		num++;
		keyMapping.Add(Keys.Y, num.ToString());
		num++;
		keyMapping.Add(Keys.U, num.ToString());
		num++;
		keyMapping.Add(Keys.I, num.ToString());
		num++;
		keyMapping.Add(Keys.O, num.ToString());
		num++;
		keyMapping.Add(Keys.P, num.ToString());
		num++;
		keyMapping.Add(Keys.OemOpenBrackets, num.ToString());
		num++;
		keyMapping.Add(Keys.OemCloseBrackets, num.ToString());
		num++;
		keyMapping.Add(Keys.OemPipe, num.ToString());
		num++;
		keyMapping.Add(Keys.NumPad7, num.ToString());
		num++;
		keyMapping.Add(Keys.NumPad8, num.ToString());
		num++;
		keyMapping.Add(Keys.NumPad9, num.ToString());
		num = 63;
		keyMapping.Add(Keys.Capital, num.ToString());
		num++;
		num++;
		keyMapping.Add(Keys.A, num.ToString());
		num++;
		keyMapping.Add(Keys.S, num.ToString());
		num++;
		keyMapping.Add(Keys.D, num.ToString());
		num++;
		keyMapping.Add(Keys.F, num.ToString());
		num++;
		keyMapping.Add(Keys.G, num.ToString());
		num++;
		keyMapping.Add(Keys.H, num.ToString());
		num++;
		keyMapping.Add(Keys.J, num.ToString());
		num++;
		keyMapping.Add(Keys.K, num.ToString());
		num++;
		keyMapping.Add(Keys.L, num.ToString());
		num++;
		keyMapping.Add(Keys.OemSemicolon, num.ToString());
		num++;
		keyMapping.Add(Keys.OemQuotes, num.ToString());
		num++;
		keyMapping.Add(Keys.Return, num.ToString());
		num = 84;
		keyMapping.Add(Keys.LShiftKey, num + ",85");
		num++;
		num++;
		keyMapping.Add(Keys.Z, num.ToString());
		num++;
		keyMapping.Add(Keys.X, num.ToString());
		num++;
		keyMapping.Add(Keys.C, num.ToString());
		num++;
		keyMapping.Add(Keys.V, num.ToString());
		num++;
		keyMapping.Add(Keys.B, num.ToString());
		num++;
		keyMapping.Add(Keys.N, num.ToString());
		num++;
		keyMapping.Add(Keys.M, num.ToString());
		num++;
		keyMapping.Add(Keys.Oemcomma, num.ToString());
		num++;
		keyMapping.Add(Keys.OemPeriod, num.ToString());
		num++;
		keyMapping.Add(Keys.OemQuestion, num.ToString());
		num++;
		keyMapping.Add(Keys.RShiftKey, num.ToString());
		num++;
		keyMapping.Add(Keys.Up, num.ToString());
		num = 105;
		keyMapping.Add(Keys.LControlKey, num.ToString());
		num++;
		keyMapping.Add(Keys.None, num.ToString());
		num++;
		keyMapping.Add(Keys.LWin, num.ToString());
		num++;
		keyMapping.Add(Keys.LMenu, num.ToString());
		num++;
		num++;
		num++;
		num++;
		keyMapping.Add(Keys.Space, num.ToString());
		num++;
		num++;
		num++;
		keyMapping.Add(Keys.RMenu, num.ToString());
		num++;
		keyMapping.Add(Keys.Apps, num.ToString());
		num++;
		keyMapping.Add(Keys.RControlKey, num.ToString());
		num++;
		keyMapping.Add(Keys.Left, num.ToString());
		num++;
		keyMapping.Add(Keys.Down, num.ToString());
		num++;
		keyMapping.Add(Keys.Right, num.ToString());
		foreach (Keys key in keys)
		{
			_ = key;
			num++;
		}
	}

	public static string GetKeyName(byte key)
	{
		StringBuilder stringBuilder = new StringBuilder(20);
		while (GetKeyNameText(key << 16, stringBuilder, stringBuilder.Capacity) == stringBuilder.Capacity - 1)
		{
			stringBuilder.Capacity *= 2;
		}
		return stringBuilder.ToString();
	}

	public static string[] GetKeyNames()
	{
		string[] array = new string[255];
		for (byte b = 0; b < 254; b++)
		{
			array[b] = GetKeyName(b);
		}
		return array;
	}
}
