using System;
using System.Runtime.InteropServices;
using System.Text.RegularExpressions;

namespace Utility;

public class SMBIOSFirmwareTable
{
	[DllImport("kernel32.dll", SetLastError = true)]
	public static extern uint GetSystemFirmwareTable(uint FirmwareTableProviderSignature, uint FirmwareTableID, IntPtr pFirmwareTableBuffer, uint BufferSize);

	public static string GetString(uint type, uint offset)
	{
		string text = "";
		try
		{
			uint num = 0u;
			num = GetSystemFirmwareTable(1381190978u, 0u, IntPtr.Zero, 0u);
			IntPtr intPtr = Marshal.AllocHGlobal((int)num);
			if (GetSystemFirmwareTable(1381190978u, 0u, intPtr, num) == num)
			{
				byte[] array = new byte[num];
				Marshal.Copy(intPtr, array, 0, (int)num);
				Marshal.FreeHGlobal(intPtr);
				text = ParseTypeData(array, num, type, offset);
				text = text.Replace("\0", string.Empty);
			}
		}
		catch
		{
		}
		return text;
	}

	private static void showMatch(string text, string expr)
	{
		Console.WriteLine("The Expression: " + expr);
		foreach (Match item in Regex.Matches(text, expr))
		{
			Console.WriteLine(item);
		}
	}

	private static string ParseTypeData(byte[] buf, uint buf_size, uint type, uint offset)
	{
		string text = "";
		if (buf_size < 8)
		{
			return "";
		}
		uint num = (uint)(buf[4] + (buf[5] << 8) + (buf[6] << 16) + (buf[7] << 24));
		uint num2;
		for (num2 = 8u; num2 < num; num2 += 2)
		{
			if (buf[num2] == type)
			{
				uint num3 = buf[num2 + 1];
				num2 += num3;
				uint num4 = 1u;
				while (buf[num2] != 0 || buf[num2 + 1] != 0)
				{
					num2++;
					text += Convert.ToChar(buf[num2]);
					if (buf[num2] == 0)
					{
						if (num4 == offset)
						{
							return text;
						}
						text = "";
						num4++;
					}
				}
				break;
			}
			uint num5 = buf[num2 + 1];
			for (num2 += num5; buf[num2] != 0 || buf[num2 + 1] != 0; num2++)
			{
			}
		}
		return "";
	}
}
