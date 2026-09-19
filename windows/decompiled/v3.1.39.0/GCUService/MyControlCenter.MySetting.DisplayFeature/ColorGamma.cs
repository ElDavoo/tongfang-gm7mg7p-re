using System;
using System.Runtime.InteropServices;

namespace MyControlCenter.MySetting.DisplayFeature;

internal class ColorGamma
{
	public struct RAMP
	{
		[MarshalAs(UnmanagedType.ByValArray, SizeConst = 256)]
		public ushort[] Red;

		[MarshalAs(UnmanagedType.ByValArray, SizeConst = 256)]
		public ushort[] Green;

		[MarshalAs(UnmanagedType.ByValArray, SizeConst = 256)]
		public ushort[] Blue;
	}

	private static bool initialized = false;

	private static int hdc;

	private static double[] _brightness = new double[3];

	private static int GammaCount = 4;

	private static int ContrastCount = 20;

	private static float[] m_gamma = new float[9] { 0.3f, 0.4f, 0.6f, 0.8f, 1f, 1.4f, 1.8f, 2.2f, 2.6f };

	private static float n = 0.02f;

	private static float[] contrast = new float[41]
	{
		0.6f + 0f * n,
		0.6f + 1f * n,
		0.6f + 2f * n,
		0.6f + 3f * n,
		0.6f + 4f * n,
		0.6f + 5f * n,
		0.6f + 6f * n,
		0.6f + 7f * n,
		0.6f + 8f * n,
		0.6f + 9f * n,
		0.6f + 10f * n,
		0.6f + 11f * n,
		0.6f + 12f * n,
		0.6f + 13f * n,
		0.6f + 14f * n,
		0.6f + 15f * n,
		0.6f + 16f * n,
		0.6f + 17f * n,
		0.6f + 18f * n,
		0.6f + 19f * n,
		0.6f + 20f * n,
		0.6f + 21f * n,
		0.6f + 22f * n,
		0.6f + 23f * n,
		0.6f + 24f * n,
		0.6f + 25f * n,
		0.6f + 26f * n,
		0.6f + 27f * n,
		0.6f + 28f * n,
		0.6f + 29f * n,
		0.6f + 30f * n,
		0.6f + 31f * n,
		0.6f + 32f * n,
		0.6f + 33f * n,
		0.6f + 34f * n,
		0.6f + 35f * n,
		0.6f + 36f * n,
		0.6f + 37f * n,
		0.6f + 38f * n,
		0.6f + 39f * n,
		0.6f + 40f * n
	};

	private static float n1 = 0.008f;

	private static float[] contrast_Intel = new float[101]
	{
		0.6f + 0f * n1,
		0.6f + 1f * n1,
		0.6f + 2f * n1,
		0.6f + 3f * n1,
		0.6f + 4f * n1,
		0.6f + 5f * n1,
		0.6f + 6f * n1,
		0.6f + 7f * n1,
		0.6f + 8f * n1,
		0.6f + 9f * n1,
		0.6f + 10f * n1,
		0.6f + 11f * n1,
		0.6f + 12f * n1,
		0.6f + 13f * n1,
		0.6f + 14f * n1,
		0.6f + 15f * n1,
		0.6f + 16f * n1,
		0.6f + 17f * n1,
		0.6f + 18f * n1,
		0.6f + 19f * n1,
		0.6f + 20f * n1,
		0.6f + 21f * n1,
		0.6f + 22f * n1,
		0.6f + 23f * n1,
		0.6f + 24f * n1,
		0.6f + 25f * n1,
		0.6f + 26f * n1,
		0.6f + 27f * n1,
		0.6f + 28f * n1,
		0.6f + 29f * n1,
		0.6f + 30f * n1,
		0.6f + 31f * n1,
		0.6f + 32f * n1,
		0.6f + 33f * n1,
		0.6f + 34f * n1,
		0.6f + 35f * n1,
		0.6f + 36f * n1,
		0.6f + 37f * n1,
		0.6f + 38f * n1,
		0.6f + 39f * n1,
		0.6f + 40f * n1,
		0.6f + 41f * n1,
		0.6f + 42f * n1,
		0.6f + 43f * n1,
		0.6f + 44f * n1,
		0.6f + 45f * n1,
		0.6f + 46f * n1,
		0.6f + 47f * n1,
		0.6f + 48f * n1,
		0.6f + 49f * n1,
		0.6f + 50f * n1,
		0.6f + 51f * n1,
		0.6f + 52f * n1,
		0.6f + 53f * n1,
		0.6f + 54f * n1,
		0.6f + 55f * n1,
		0.6f + 56f * n1,
		0.6f + 57f * n1,
		0.6f + 58f * n1,
		0.6f + 59f * n1,
		0.6f + 60f * n1,
		0.6f + 61f * n1,
		0.6f + 62f * n1,
		0.6f + 63f * n1,
		0.6f + 64f * n1,
		0.6f + 65f * n1,
		0.6f + 66f * n1,
		0.6f + 67f * n1,
		0.6f + 68f * n1,
		0.6f + 69f * n1,
		0.6f + 70f * n1,
		0.6f + 71f * n1,
		0.6f + 72f * n1,
		0.6f + 73f * n1,
		0.6f + 74f * n1,
		0.6f + 75f * n1,
		0.6f + 76f * n1,
		0.6f + 77f * n1,
		0.6f + 78f * n1,
		0.6f + 79f * n1,
		0.6f + 80f * n1,
		0.6f + 81f * n1,
		0.6f + 82f * n1,
		0.6f + 83f * n1,
		0.6f + 84f * n1,
		0.6f + 85f * n1,
		0.6f + 86f * n1,
		0.6f + 87f * n1,
		0.6f + 88f * n1,
		0.6f + 89f * n1,
		0.6f + 90f * n1,
		0.6f + 91f * n1,
		0.6f + 92f * n1,
		0.6f + 93f * n1,
		0.6f + 94f * n1,
		0.6f + 95f * n1,
		0.6f + 96f * n1,
		0.6f + 97f * n1,
		0.6f + 98f * n1,
		0.6f + 99f * n1,
		0.6f + 100f * n1
	};

	[DllImport("user32.dll", ExactSpelling = true)]
	public static extern IntPtr GetDC(IntPtr hWnd);

	[DllImport("kernel32.dll")]
	public static extern uint GetLastError();

	[DllImport("kernel32.dll", SetLastError = true)]
	private static extern bool SetVolumeLabel(string lpRootPathName, string lpVolumeName);

	[DllImport("gdi32.dll", ExactSpelling = true)]
	public static extern bool SetDeviceGammaRamp(IntPtr hDC, ref RAMP lpRamp);

	public static void SetGamma(int nCount)
	{
		if (nCount > 8)
		{
			nCount = 8;
		}
		else if (nCount < 0)
		{
			nCount = 0;
		}
		GammaCount = nCount;
	}

	public static void SetBrightness(int RBright, int GBright, int BBright)
	{
		if (RBright > 100)
		{
			RBright = 100;
		}
		if (GBright > 100)
		{
			GBright = 100;
		}
		if (BBright > 100)
		{
			BBright = 100;
		}
		_brightness[0] = RBright;
		_brightness[1] = GBright;
		_brightness[2] = BBright;
	}

	public static void SetContrast(int nCount, bool isIntel = false)
	{
		if (isIntel)
		{
			if (nCount > 100)
			{
				nCount = 100;
			}
			else if (nCount < 0)
			{
				nCount = 0;
			}
		}
		else if (nCount > 40)
		{
			nCount = 40;
		}
		else if (nCount < 0)
		{
			nCount = 0;
		}
		ContrastCount = nCount;
	}

	public static bool UpdateRamps(IntPtr hdc, bool isIntel = false)
	{
		float[] array = contrast;
		if (isIntel)
		{
			array = contrast_Intel;
		}
		RAMP lpRamp = new RAMP
		{
			Red = new ushort[256],
			Green = new ushort[256],
			Blue = new ushort[256]
		};
		for (int i = 0; i < 3; i++)
		{
			for (int j = 0; j < 256; j++)
			{
				double num = (double)array[ContrastCount] * (Math.Pow((double)j / 256.0, 1.0 / (double)m_gamma[GammaCount]) * 65535.0) + _brightness[i] * 255.0;
				if (num > 65535.0)
				{
					num = 65535.0;
				}
				if (num < 0.0)
				{
					num = 0.0;
				}
				switch (i)
				{
				case 0:
					lpRamp.Red[j] = (ushort)num;
					break;
				case 1:
					lpRamp.Green[j] = (ushort)num;
					break;
				case 2:
					lpRamp.Blue[j] = (ushort)num;
					break;
				}
			}
		}
		return SetDeviceGammaRamp(hdc, ref lpRamp);
	}
}
