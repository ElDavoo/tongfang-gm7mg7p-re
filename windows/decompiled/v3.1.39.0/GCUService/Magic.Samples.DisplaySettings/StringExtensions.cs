using System;

namespace Magic.Samples.DisplaySettings;

public static class StringExtensions
{
	public static byte[] ToLPTStr(this string str)
	{
		byte[] array = new byte[str.Length + 1];
		int num = 0;
		char[] array2 = str.ToCharArray();
		foreach (char value in array2)
		{
			array[num++] = Convert.ToByte(value);
		}
		array[num] = Convert.ToByte('\0');
		return array;
	}
}
