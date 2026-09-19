using System;
using System.Collections.Generic;
using System.Runtime.InteropServices;
using MyControlCenter;

namespace Utility;

internal class UtilityExtensions
{
	public static uint ModeSwitchClockWise(uint currentMode, bool clockwise)
	{
		List<uint> list = new List<uint> { 0u, 1u, 2u };
		uint num = currentMode;
		if (clockwise)
		{
			int num2 = list.FindIndex((uint n) => n.Equals(currentMode));
			num2++;
			num2 = ((num2 <= 2) ? num2 : 0);
			return list[num2];
		}
		int num3 = list.FindIndex((uint n) => n.Equals(currentMode));
		num3--;
		num3 = ((num3 < 0) ? 2 : num3);
		return list[num3];
	}

	public static int GetBitFromByte(byte data, int num)
	{
		return (data >> num) & 1;
	}

	public static byte[] Combine(byte[] first, byte[] second)
	{
		byte[] array = new byte[first.Length + second.Length];
		Buffer.BlockCopy(first, 0, array, 0, first.Length);
		Buffer.BlockCopy(second, 0, array, first.Length, second.Length);
		return array;
	}

	public static T BytesToStructure<T>(byte[] bytes)
	{
		int num = Marshal.SizeOf(typeof(T));
		if (bytes.Length < num)
		{
			throw new Exception("Invalid parameter");
		}
		IntPtr intPtr = Marshal.AllocHGlobal(num);
		try
		{
			Marshal.Copy(bytes, 0, intPtr, num);
			return (T)Marshal.PtrToStructure(intPtr, typeof(T));
		}
		finally
		{
			Marshal.FreeHGlobal(intPtr);
		}
	}

	public static bool IsNvGpu()
	{
		if (new HardwareInfoCollect().getGraphicInfo().Contains("NVIDIA"))
		{
			return true;
		}
		return false;
	}
}
