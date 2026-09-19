using System;
using MyECIO;

namespace LightingModel;

public static class WKDColor
{
	private const ulong m_SupportByte4 = 1853uL;

	private const ulong m_SupportByte5 = 1858uL;

	private const ulong m_SupportByte6 = 1934uL;

	private const byte m_bitLiteon_glossy = 4;

	private const byte m_bitEverlight = 8;

	private const byte m_bitLiteon_CIE_JP = 64;

	private const byte m_bitLiteon_CIE_USUK = 128;

	private const byte m_bitEverlight_CIE = 1;

	private const byte m_bitLiteon_CIE_FromFW = 4;

	private const byte m_bitEverlight_CIE_FromFW = 8;

	private static VENDOR m_LED_Vender;

	private const byte m_bitLiteon_cloudy = 128;

	internal const byte EC_PROJECT_GK5CN_X = 6;

	internal const byte EC_PROJECT_GK7CN_S = 7;

	internal const byte EC_PROJECT_IDP = 11;

	internal const byte EC_PROJECT_ID6Y = 12;

	internal const byte EC_PROJECT_ID7Y = 13;

	static WKDColor()
	{
		m_LED_Vender = VENDOR.LITEON_CLOUDY;
		byte Data = 0;
		MyEcCtrl.Instance.Read("WKDColor", 1858, ref Data);
		byte b = (byte)(Convert.ToUInt64(Data) & 0xFF);
		if ((b & 4) == 4)
		{
			m_LED_Vender = VENDOR.LITEON_GLOSSY;
			return;
		}
		if ((b & 8) == 8)
		{
			m_LED_Vender = VENDOR.EVERGREEN;
			return;
		}
		if ((b & 0x40) == 64)
		{
			m_LED_Vender = VENDOR.LITEON_CIE_JP;
			return;
		}
		if ((b & 0x80) == 128)
		{
			m_LED_Vender = VENDOR.LITEON_CIE_USUK;
			return;
		}
		Data = 0;
		MyEcCtrl.Instance.Read("WKDColor", 1853, ref Data);
		b = (byte)(Convert.ToUInt64(Data) & 0xFF);
		if ((b & 0x80) == 128)
		{
			m_LED_Vender = VENDOR.LITEON_CLOUDY;
		}
		MyEcCtrl.Instance.Read("WKDColor", 1934, ref Data);
		b = (byte)(Convert.ToUInt64(Data) & 0xFF);
		if ((b & 0x80) == 1)
		{
			m_LED_Vender = VENDOR.EVERGREEN_CIE;
		}
	}

	public static void SetLEDVenorFromFirmware(byte FWData)
	{
		if (FWData == 8)
		{
			m_LED_Vender = VENDOR.EVERGREEN_CIE;
		}
		else
		{
			m_LED_Vender = VENDOR.LITEON_CIE_USUK;
		}
	}

	public static RGB_S cheatRGB_2ndME(byte R, byte G, byte B)
	{
		RGB_S result = default(RGB_S);
		if (m_LED_Vender == VENDOR.LITEON_GLOSSY)
		{
			if (R == byte.MaxValue && G == byte.MaxValue && B == byte.MaxValue)
			{
				result.R = byte.MaxValue;
				result.G = 50;
				result.B = 170;
			}
			else if (R == byte.MaxValue && G == 165 && B == 0)
			{
				result.R = byte.MaxValue;
				result.G = 19;
				result.B = 0;
			}
			else if (R == byte.MaxValue && G == byte.MaxValue && B == 0)
			{
				result.R = byte.MaxValue;
				result.G = 50;
				result.B = 0;
			}
			else if (R == 0 && G == byte.MaxValue && B == byte.MaxValue)
			{
				result.R = 0;
				result.G = 50;
				result.B = 170;
			}
			else if (R == 139 && G == 0 && B == byte.MaxValue)
			{
				result.R = 138;
				result.G = 0;
				result.B = 170;
			}
			else if (R > 249 && G < 20 && B < 128)
			{
				if (B < 100)
				{
					result.R = R;
					result.G = G;
					result.B = (byte)(B / 10);
				}
				else
				{
					result.R = R;
					result.G = G;
					result.B = (byte)(B - 10);
				}
			}
			else if (R < 20 && B < G)
			{
				result.R = R;
				result.G = G;
				result.B = (byte)(170 * B / 255);
			}
			else if (G < 20 && R < B)
			{
				result.R = R;
				result.G = G;
				result.B = B;
			}
			else
			{
				result.R = R;
				result.G = (byte)(50 * G / 255);
				result.B = (byte)(170 * B / 255);
			}
		}
		else if (m_LED_Vender == VENDOR.EVERGREEN)
		{
			if (R == byte.MaxValue && G == byte.MaxValue && B == byte.MaxValue)
			{
				result.R = byte.MaxValue;
				result.G = 110;
				result.B = 120;
			}
			else if (R == byte.MaxValue && G == 165 && B == 0)
			{
				result.R = byte.MaxValue;
				result.G = 30;
				result.B = 0;
			}
			else if (R == 241 && G == 90 && B == 36)
			{
				result.R = byte.MaxValue;
				result.G = 5;
				result.B = 0;
			}
			else if (R == 247 && G == 147 && B == 30)
			{
				result.R = byte.MaxValue;
				result.G = 15;
				result.B = 0;
			}
			else if (R == byte.MaxValue && G == byte.MaxValue && B == 0)
			{
				result.R = byte.MaxValue;
				result.G = 50;
				result.B = 0;
			}
			else if (R == 0 && G == byte.MaxValue && B == byte.MaxValue)
			{
				result.R = 0;
				result.G = 110;
				result.B = 120;
			}
			else if (R == 139 && G == 0 && B == byte.MaxValue)
			{
				result.R = byte.MaxValue;
				result.G = 0;
				result.B = 120;
			}
			else if (R > 249 && G < 20 && B < 128)
			{
				if (B < 100)
				{
					result.R = R;
					result.G = G;
					result.B = (byte)(B / 10);
				}
				else
				{
					result.R = R;
					result.G = G;
					result.B = (byte)(B - 10);
				}
			}
			else if (R < 20 && B < G)
			{
				result.R = R;
				result.G = G;
				result.B = (byte)(80 * B / 255);
			}
			else if (G < 20 && R < B)
			{
				result.R = R;
				result.G = G;
				result.B = B;
			}
			else
			{
				result.R = R;
				result.G = (byte)(110 * G / 255);
				result.B = (byte)(120 * B / 255);
			}
		}
		else if (m_LED_Vender == VENDOR.LITEON_CIE_JP || m_LED_Vender == VENDOR.LITEON_CIE_USUK)
		{
			if (R == byte.MaxValue && G == byte.MaxValue && B == byte.MaxValue)
			{
				result.R = 220;
				result.G = 120;
				result.B = 110;
			}
			else if (R == byte.MaxValue && G == 165 && B == 0)
			{
				result.R = 220;
				result.G = 30;
				result.B = 0;
			}
			else if (R == byte.MaxValue && G == byte.MaxValue && B == 0)
			{
				result.R = 220;
				result.G = 120;
				result.B = 0;
			}
			else if (R == 0 && G == byte.MaxValue && B == byte.MaxValue)
			{
				result.R = 0;
				result.G = 120;
				result.B = 110;
			}
			else if (R == 139 && G == 0 && B == byte.MaxValue)
			{
				result.R = 220;
				result.G = 0;
				result.B = 110;
			}
			else
			{
				result.R = (byte)(220 * R / 255);
				result.G = (byte)(120 * G / 255);
				result.B = (byte)(110 * B / 255);
			}
		}
		else if (m_LED_Vender == VENDOR.EVERGREEN_CIE)
		{
			if (R == byte.MaxValue && G == byte.MaxValue && B == byte.MaxValue)
			{
				result.R = 220;
				result.G = 95;
				result.B = 160;
			}
			else if (R == byte.MaxValue && G == 165 && B == 0)
			{
				result.R = 250;
				result.G = 30;
				result.B = 0;
			}
			else if (R == byte.MaxValue && G == byte.MaxValue && B == 0)
			{
				result.R = 220;
				result.G = 95;
				result.B = 0;
			}
			else if (R == 0 && G == byte.MaxValue && B == byte.MaxValue)
			{
				result.R = 0;
				result.G = 95;
				result.B = 160;
			}
			else if (R == 139 && G == 0 && B == byte.MaxValue)
			{
				result.R = 220;
				result.G = 0;
				result.B = 160;
			}
			else
			{
				result.R = (byte)(220 * R / 255);
				result.G = (byte)(95 * G / 255);
				result.B = (byte)(160 * B / 255);
			}
		}
		else if (R == byte.MaxValue && G == byte.MaxValue && B == byte.MaxValue)
		{
			result.R = byte.MaxValue;
			result.G = 180;
			result.B = 200;
		}
		else if (R == byte.MaxValue && G == 165 && B == 0)
		{
			result.R = byte.MaxValue;
			result.G = 42;
			result.B = 0;
		}
		else if (R == 241 && G == 90 && B == 36)
		{
			result.R = byte.MaxValue;
			result.G = 25;
			result.B = 0;
		}
		else if (R == 247 && G == 147 && B == 30)
		{
			result.R = byte.MaxValue;
			result.G = 42;
			result.B = 0;
		}
		else if (R == byte.MaxValue && G == byte.MaxValue && B == 0)
		{
			result.R = byte.MaxValue;
			result.G = 180;
			result.B = 0;
		}
		else if (R == 0 && G == byte.MaxValue && B == byte.MaxValue)
		{
			result.R = 0;
			result.G = 180;
			result.B = 200;
		}
		else if (R == 139 && G == 0 && B == byte.MaxValue)
		{
			result.R = 138;
			result.G = 0;
			result.B = 200;
		}
		else if (R > 249 && G < 20 && B < 128)
		{
			if (B < 100)
			{
				result.R = R;
				result.G = G;
				result.B = (byte)(B / 10);
			}
			else
			{
				result.R = R;
				result.G = G;
				result.B = (byte)(B - 10);
			}
		}
		else if (R < 20 && B < G)
		{
			result.R = R;
			result.G = G;
			result.B = (byte)(200 * B / 255);
		}
		else if (G < 20 && R < B)
		{
			result.R = R;
			result.G = G;
			result.B = B;
		}
		else
		{
			result.R = R;
			result.G = (byte)(180 * G / 255);
			result.B = (byte)(200 * B / 255);
		}
		return result;
	}

	public static RGB_S cheatRGB_2p1ndME(byte R, byte G, byte B)
	{
		RGB_S result = default(RGB_S);
		if (R == byte.MaxValue && G == byte.MaxValue && B == byte.MaxValue)
		{
			result.R = byte.MaxValue;
			result.G = 100;
			result.B = 80;
		}
		else if (R == byte.MaxValue && G == 165 && B == 0)
		{
			result.R = byte.MaxValue;
			result.G = 30;
			result.B = 0;
		}
		else if (R == byte.MaxValue && G == byte.MaxValue && B == 0)
		{
			result.R = byte.MaxValue;
			result.G = 100;
			result.B = 0;
		}
		else if (R == 0 && G == byte.MaxValue && B == byte.MaxValue)
		{
			result.R = 0;
			result.G = 100;
			result.B = 80;
		}
		else if (R == 139 && G == 0 && B == byte.MaxValue)
		{
			result.R = byte.MaxValue;
			result.G = 0;
			result.B = 80;
		}
		else
		{
			result.R = R;
			result.G = (byte)(100 * G / 255);
			result.B = (byte)(80 * B / 255);
		}
		return result;
	}

	public static RGB_S cheatRGB_2p2ndME(byte R, byte G, byte B)
	{
		RGB_S result = default(RGB_S);
		if (m_LED_Vender == VENDOR.EVERGREEN_CIE)
		{
			result.R = R;
			result.G = (byte)(70 * G / 255);
			result.B = (byte)(80 * B / 255);
			if (R == byte.MaxValue && G == 165 && B == 0)
			{
				result.R = byte.MaxValue;
				result.G = 25;
				result.B = 0;
			}
		}
		else
		{
			result.R = (byte)(220 * R / 255);
			result.G = (byte)(120 * G / 255);
			result.B = (byte)(110 * B / 255);
			if (R == byte.MaxValue && G == 165 && B == 0)
			{
				result.R = 220;
				result.G = 30;
				result.B = 0;
			}
		}
		return result;
	}

	public static RGB_S cheatRGB_4Zone(byte ProjectID, byte R, byte G, byte B)
	{
		RGB_S result = default(RGB_S);
		if (ProjectID == 6 || ProjectID == 7)
		{
			if (R == byte.MaxValue && G == 165 && B == 0)
			{
				result.R = byte.MaxValue;
				result.G = 60;
				result.B = 0;
			}
			else if (R == byte.MaxValue && G == byte.MaxValue && B == 0)
			{
				result.R = byte.MaxValue;
				result.G = 120;
				result.B = 0;
			}
			else
			{
				result.R = R;
				result.G = (byte)(120 * G / 255);
				result.B = (byte)(220 * B / 255);
			}
		}
		else if (R == byte.MaxValue && G == 100 && B == 0)
		{
			result.R = byte.MaxValue;
			result.G = 40;
			result.B = 0;
		}
		else if (R == byte.MaxValue && G == 165 && B == 0)
		{
			result.R = byte.MaxValue;
			result.G = 70;
			result.B = 0;
		}
		else
		{
			result.R = R;
			result.G = (byte)(100 * G / 255);
			result.B = (byte)(200 * B / 255);
		}
		return result;
	}

	public static RGB_S cheatRGB_HIDLightbar(byte R, byte G, byte B)
	{
		RGB_S result = default(RGB_S);
		if (R == byte.MaxValue && G == byte.MaxValue && B == byte.MaxValue)
		{
			result.R = 220;
			result.G = 120;
			result.B = 110;
		}
		else if (R == byte.MaxValue && G == 165 && B == 0)
		{
			result.R = 220;
			result.G = 30;
			result.B = 0;
		}
		else if (R == byte.MaxValue && G == byte.MaxValue && B == 0)
		{
			result.R = 220;
			result.G = 120;
			result.B = 0;
		}
		else if (R == 0 && G == byte.MaxValue && B == byte.MaxValue)
		{
			result.R = 0;
			result.G = 60;
			result.B = 110;
		}
		else if (R == 139 && G == 0 && B == byte.MaxValue)
		{
			result.R = 220;
			result.G = 0;
			result.B = 110;
		}
		else
		{
			result.R = (byte)(220 * R / 255);
			result.G = (byte)(120 * G / 255);
			result.B = (byte)(110 * B / 255);
		}
		return result;
	}

	public static RGB_S cheatRGB_HIDLightbar2(byte R, byte G, byte B)
	{
		RGB_S result = default(RGB_S);
		if (R == byte.MaxValue && G == byte.MaxValue && B == byte.MaxValue)
		{
			result.R = 220;
			result.G = 100;
			result.B = 100;
		}
		else if (R == byte.MaxValue && G == 165 && B == 0)
		{
			result.R = byte.MaxValue;
			result.G = 45;
			result.B = 0;
		}
		else if (R == byte.MaxValue && G == byte.MaxValue && B == 0)
		{
			result.R = byte.MaxValue;
			result.G = 115;
			result.B = 0;
		}
		else
		{
			result.R = (byte)(255 * R / 255);
			result.G = (byte)(100 * G / 255);
			result.B = (byte)(100 * B / 255);
		}
		return result;
	}
}
