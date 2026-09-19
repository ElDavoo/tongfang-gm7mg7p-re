using System.Runtime.InteropServices;
using System.Threading;

namespace GCUService.MySetting;

internal class MyMagSetFullscreenColorEffect
{
	public struct MAGCOLOREFFECT
	{
		[MarshalAs(UnmanagedType.ByValArray, SizeConst = 25)]
		public float[] transform;
	}

	private const string Magnification = "Magnification.dll";

	private object Saturationlock = new object();

	[DllImport("Magnification.dll", ExactSpelling = true, SetLastError = true)]
	public static extern bool MagInitialize();

	[DllImport("Magnification.dll", ExactSpelling = true, SetLastError = true)]
	public static extern bool MagUninitialize();

	[DllImport("Magnification.dll", ExactSpelling = true, SetLastError = true)]
	public static extern bool MagSetFullscreenColorEffect(ref MAGCOLOREFFECT pEffect);

	public void ContrastMartrixSetting(float c = 1f)
	{
		float num = (1f - c) / 2f;
		float[] transform = new float[25]
		{
			c, 0f, 0f, 0f, 0f, 0f, c, 0f, 0f, 0f,
			0f, 0f, c, 0f, 0f, 0f, 0f, 0f, 1f, 0f,
			num, num, num, 0f, 1f
		};
		MAGCOLOREFFECT pEffect = new MAGCOLOREFFECT
		{
			transform = transform
		};
		MagSetFullscreenColorEffect(ref pEffect);
	}

	public void SaturationMartrixSetting(float s = 1f)
	{
		if (Monitor.TryEnter(Saturationlock, 1000))
		{
			try
			{
				float num = 0.3086f;
				float num2 = 0.6094f;
				float num3 = 0.082f;
				float num4 = (1f - s) * num;
				float num5 = (1f - s) * num2;
				float num6 = (1f - s) * num3;
				float[] transform = new float[25]
				{
					num4 + s,
					num4,
					num4,
					0f,
					0f,
					num5,
					num5 + s,
					num5,
					0f,
					0f,
					num6,
					num6,
					num6 + s,
					0f,
					0f,
					0f,
					0f,
					0f,
					1f,
					0f,
					0f,
					0f,
					0f,
					0f,
					1f
				};
				MAGCOLOREFFECT pEffect = new MAGCOLOREFFECT
				{
					transform = transform
				};
				MagInitialize();
				MagSetFullscreenColorEffect(ref pEffect);
			}
			finally
			{
				Monitor.Exit(Saturationlock);
			}
		}
	}
}
