using System.Linq;
using LightingModel;

namespace MyControlCenter.MyRgbKeyboard;

internal class HIDKeyboardFactory
{
	public static HIDKeyboard CreateHIDDevice(LM_Manager lm_Manger)
	{
		_ = lm_Manger.m_KB_Solution;
		string text = lm_Manger.LM_GetFirmwareVersion();
		switch (lm_Manger.m_KB_Type)
		{
		case RGBKB_Type.FourZone:
			return new FourZoneKeyboard(lm_Manger, text);
		case RGBKB_Type.MEZone_2nd_101:
			return new HIDKeyboard(lm_Manger, text);
		case RGBKB_Type.MEZone_2nd_102:
			return new HIDKeyboard(lm_Manger, text);
		case RGBKB_Type.MEZone_2p1nd_85:
		case RGBKB_Type.MEZone_2p1nd_86:
		case RGBKB_Type.MEZone_2p1nd_87:
		case RGBKB_Type.MEZone_2p1nd_88:
			if (text.Split('.').First() == "16")
			{
				return new _2p1ndKeyboard_KC(lm_Manger, text);
			}
			if (text.Split('.').First() == "13")
			{
				return new _2p1ndKeyboard_QC(lm_Manger, text);
			}
			return new _2p1ndkeyboard(lm_Manger, text);
		case RGBKB_Type.MEZone_2p2nd_97:
		case RGBKB_Type.MEZone_2p2nd_98:
		case RGBKB_Type.MEZone_2p2nd_99:
		case RGBKB_Type.MEZone_2p2nd_100:
			return new _2p2ndkeyboard(lm_Manger, text);
		case RGBKB_Type.MEZone_Lighbar:
			return new HIDLightbar(lm_Manger, text);
		case RGBKB_Type.MEZone_Lighbar2:
			return new HIDLightbar2(lm_Manger, text);
		case RGBKB_Type.SingleZone:
			return new SingleZone(lm_Manger, text);
		case RGBKB_Type.FourZoneSingleColor:
			return new FourZoneSingleColorKeyboard(lm_Manger, text);
		default:
			return null;
		}
	}

	public static string GetFWVersion()
	{
		return "";
	}
}
