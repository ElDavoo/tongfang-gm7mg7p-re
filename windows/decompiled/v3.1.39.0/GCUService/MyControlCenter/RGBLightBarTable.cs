using System.Collections.Generic;
using System.Threading;
using MyECIO;
using UsbHidModel;
using Utility;

namespace MyControlCenter;

internal static class RGBLightBarTable
{
	private static MyEcCtrl EcCtrl = MyEcCtrl.Instance;

	private static string m_ClassName = "RGBLightBarTable";

	private static HIDManager m_HIDManager = new HIDManager();

	private static uint _R_PWM_Lev0 = 0u;

	private static uint _R_PWM_Lev1 = 40u;

	private static uint _R_PWM_Lev2 = 60u;

	private static uint _R_PWM_Lev3 = 80u;

	private static uint _R_PWM_Lev4 = 100u;

	private static uint _R_PWM_Lev5 = 120u;

	private static uint _R_PWM_Lev6 = 140u;

	private static uint _R_PWM_Lev7 = 160u;

	private static uint _R_PWM_Lev8 = 180u;

	private static uint _R_PWM_Lev9 = 200u;

	private static uint _G_PWM_Lev0 = 0u;

	private static uint _G_PWM_Lev1 = 40u;

	private static uint _G_PWM_Lev2 = 60u;

	private static uint _G_PWM_Lev3 = 80u;

	private static uint _G_PWM_Lev4 = 100u;

	private static uint _G_PWM_Lev5 = 120u;

	private static uint _G_PWM_Lev6 = 140u;

	private static uint _G_PWM_Lev7 = 160u;

	private static uint _G_PWM_Lev8 = 180u;

	private static uint _G_PWM_Lev9 = 200u;

	private static uint _B_PWM_Lev0 = 0u;

	private static uint _B_PWM_Lev1 = 40u;

	private static uint _B_PWM_Lev2 = 60u;

	private static uint _B_PWM_Lev3 = 80u;

	private static uint _B_PWM_Lev4 = 100u;

	private static uint _B_PWM_Lev5 = 120u;

	private static uint _B_PWM_Lev6 = 140u;

	private static uint _B_PWM_Lev7 = 160u;

	private static uint _B_PWM_Lev8 = 180u;

	private static uint _B_PWM_Lev9 = 200u;

	public static void Init(int nProjectID)
	{
		switch (nProjectID)
		{
		case 6:
		case 10:
			LogCtrl.TraceMessage("EcProjectID: " + nProjectID + ", follow X Series Table.", "Init", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\MyRgbLightbar\\MyRgbLightbarDefault.cs", 757);
			_R_PWM_Lev0 = 0u;
			_R_PWM_Lev1 = 40u;
			_R_PWM_Lev2 = 60u;
			_R_PWM_Lev3 = 80u;
			_R_PWM_Lev4 = 100u;
			_R_PWM_Lev5 = 120u;
			_R_PWM_Lev6 = 140u;
			_R_PWM_Lev7 = 160u;
			_R_PWM_Lev8 = 180u;
			_R_PWM_Lev9 = 200u;
			_G_PWM_Lev0 = 0u;
			_G_PWM_Lev1 = 40u;
			_G_PWM_Lev2 = 60u;
			_G_PWM_Lev3 = 80u;
			_G_PWM_Lev4 = 100u;
			_G_PWM_Lev5 = 120u;
			_G_PWM_Lev6 = 140u;
			_G_PWM_Lev7 = 160u;
			_G_PWM_Lev8 = 165u;
			_G_PWM_Lev9 = 170u;
			_B_PWM_Lev0 = 0u;
			_B_PWM_Lev1 = 40u;
			_B_PWM_Lev2 = 60u;
			_B_PWM_Lev3 = 80u;
			_B_PWM_Lev4 = 100u;
			_B_PWM_Lev5 = 120u;
			_B_PWM_Lev6 = 140u;
			_B_PWM_Lev7 = 160u;
			_B_PWM_Lev8 = 170u;
			_B_PWM_Lev9 = 180u;
			break;
		case 7:
			LogCtrl.TraceMessage("EcProjectID: " + nProjectID + ", follow S Series Table.", "Init", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\MyRgbLightbar\\MyRgbLightbarDefault.cs", 791);
			_R_PWM_Lev0 = 0u;
			_R_PWM_Lev1 = 13u;
			_R_PWM_Lev2 = 26u;
			_R_PWM_Lev3 = 39u;
			_R_PWM_Lev4 = 52u;
			_R_PWM_Lev5 = 65u;
			_R_PWM_Lev6 = 78u;
			_R_PWM_Lev7 = 91u;
			_R_PWM_Lev8 = 104u;
			_R_PWM_Lev9 = 117u;
			_G_PWM_Lev0 = 0u;
			_G_PWM_Lev1 = 15u;
			_G_PWM_Lev2 = 30u;
			_G_PWM_Lev3 = 45u;
			_G_PWM_Lev4 = 60u;
			_G_PWM_Lev5 = 75u;
			_G_PWM_Lev6 = 90u;
			_G_PWM_Lev7 = 105u;
			_G_PWM_Lev8 = 120u;
			_G_PWM_Lev9 = 135u;
			_B_PWM_Lev0 = 0u;
			_B_PWM_Lev1 = 9u;
			_B_PWM_Lev2 = 18u;
			_B_PWM_Lev3 = 27u;
			_B_PWM_Lev4 = 36u;
			_B_PWM_Lev5 = 45u;
			_B_PWM_Lev6 = 54u;
			_B_PWM_Lev7 = 63u;
			_B_PWM_Lev8 = 72u;
			_B_PWM_Lev9 = 81u;
			break;
		case 3:
			LogCtrl.TraceMessage("EcProjectID: " + nProjectID + ", follow GKZ Series Table.", "Init", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\MyRgbLightbar\\MyRgbLightbarDefault.cs", 825);
			_R_PWM_Lev0 = 0u;
			_R_PWM_Lev1 = 40u;
			_R_PWM_Lev2 = 60u;
			_R_PWM_Lev3 = 80u;
			_R_PWM_Lev4 = 100u;
			_R_PWM_Lev5 = 120u;
			_R_PWM_Lev6 = 140u;
			_R_PWM_Lev7 = 160u;
			_R_PWM_Lev8 = 180u;
			_R_PWM_Lev9 = 200u;
			_G_PWM_Lev0 = 0u;
			_G_PWM_Lev1 = 13u;
			_G_PWM_Lev2 = 26u;
			_G_PWM_Lev3 = 39u;
			_G_PWM_Lev4 = 52u;
			_G_PWM_Lev5 = 65u;
			_G_PWM_Lev6 = 78u;
			_G_PWM_Lev7 = 91u;
			_G_PWM_Lev8 = 104u;
			_G_PWM_Lev9 = 117u;
			_B_PWM_Lev0 = 0u;
			_B_PWM_Lev1 = 7u;
			_B_PWM_Lev2 = 14u;
			_B_PWM_Lev3 = 21u;
			_B_PWM_Lev4 = 28u;
			_B_PWM_Lev5 = 35u;
			_B_PWM_Lev6 = 42u;
			_B_PWM_Lev7 = 49u;
			_B_PWM_Lev8 = 56u;
			_B_PWM_Lev9 = 63u;
			break;
		default:
			LogCtrl.TraceMessage("EcProjectID: " + nProjectID + ", follow Default Table.", "Init", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\MyRgbLightbar\\MyRgbLightbarDefault.cs", 897);
			_R_PWM_Lev0 = 0u;
			_R_PWM_Lev1 = 40u;
			_R_PWM_Lev2 = 60u;
			_R_PWM_Lev3 = 80u;
			_R_PWM_Lev4 = 100u;
			_R_PWM_Lev5 = 120u;
			_R_PWM_Lev6 = 140u;
			_R_PWM_Lev7 = 160u;
			_R_PWM_Lev8 = 180u;
			_R_PWM_Lev9 = 200u;
			_G_PWM_Lev0 = 0u;
			_G_PWM_Lev1 = 40u;
			_G_PWM_Lev2 = 60u;
			_G_PWM_Lev3 = 80u;
			_G_PWM_Lev4 = 100u;
			_G_PWM_Lev5 = 120u;
			_G_PWM_Lev6 = 140u;
			_G_PWM_Lev7 = 160u;
			_G_PWM_Lev8 = 180u;
			_G_PWM_Lev9 = 200u;
			_B_PWM_Lev0 = 0u;
			_B_PWM_Lev1 = 40u;
			_B_PWM_Lev2 = 60u;
			_B_PWM_Lev3 = 80u;
			_B_PWM_Lev4 = 100u;
			_B_PWM_Lev5 = 120u;
			_B_PWM_Lev6 = 140u;
			_B_PWM_Lev7 = 160u;
			_B_PWM_Lev8 = 180u;
			_B_PWM_Lev9 = 200u;
			break;
		}
	}

	public static ulong GetTable(string Table, uint InputLevel)
	{
		ulong result = 0uL;
		switch (Table)
		{
		case "Red":
			switch (InputLevel)
			{
			case 0u:
				result = _R_PWM_Lev0;
				break;
			case 1u:
				result = _R_PWM_Lev1;
				break;
			case 2u:
				result = _R_PWM_Lev2;
				break;
			case 3u:
				result = _R_PWM_Lev3;
				break;
			case 4u:
				result = _R_PWM_Lev4;
				break;
			case 5u:
				result = _R_PWM_Lev5;
				break;
			case 6u:
				result = _R_PWM_Lev6;
				break;
			case 7u:
				result = _R_PWM_Lev7;
				break;
			case 8u:
				result = _R_PWM_Lev8;
				break;
			case 9u:
				result = _R_PWM_Lev9;
				break;
			}
			break;
		case "Green":
			switch (InputLevel)
			{
			case 0u:
				result = _G_PWM_Lev0;
				break;
			case 1u:
				result = _G_PWM_Lev1;
				break;
			case 2u:
				result = _G_PWM_Lev2;
				break;
			case 3u:
				result = _G_PWM_Lev3;
				break;
			case 4u:
				result = _G_PWM_Lev4;
				break;
			case 5u:
				result = _G_PWM_Lev5;
				break;
			case 6u:
				result = _G_PWM_Lev6;
				break;
			case 7u:
				result = _G_PWM_Lev7;
				break;
			case 8u:
				result = _G_PWM_Lev8;
				break;
			case 9u:
				result = _G_PWM_Lev9;
				break;
			}
			break;
		case "Blue":
			switch (InputLevel)
			{
			case 0u:
				result = _B_PWM_Lev0;
				break;
			case 1u:
				result = _B_PWM_Lev1;
				break;
			case 2u:
				result = _B_PWM_Lev2;
				break;
			case 3u:
				result = _B_PWM_Lev3;
				break;
			case 4u:
				result = _B_PWM_Lev4;
				break;
			case 5u:
				result = _B_PWM_Lev5;
				break;
			case 6u:
				result = _B_PWM_Lev6;
				break;
			case 7u:
				result = _B_PWM_Lev7;
				break;
			case 8u:
				result = _B_PWM_Lev8;
				break;
			case 9u:
				result = _B_PWM_Lev9;
				break;
			}
			break;
		}
		return result;
	}

	private static bool IsKeyboard_MEZone_2p2nd()
	{
		bool result = false;
		List<ushort> obj = new List<ushort> { 52736, 24576, 24577, 24578, 24579, 24580, 24582, 6007 };
		byte Ver_High = 0;
		byte Ver_Low = 0;
		byte Ver_Test = 0;
		byte Ver_Customer = 0;
		foreach (ushort item in obj)
		{
			if (m_HIDManager.Init(1165, item, 1))
			{
				HID_Get_FirmwareVersion_80H(ref Ver_High, ref Ver_Low, ref Ver_Test, ref Ver_Customer);
				if (m_HIDManager.GetUsagePage() == 65283 && Ver_High == 20)
				{
					result = true;
				}
			}
		}
		LogCtrl.Write(m_ClassName + " | IsKeyboard_MEZone_2p2nd | Is2p2nd: " + result);
		return result;
	}

	private static bool HID_Get_FirmwareVersion_80H(ref byte Ver_High, ref byte Ver_Low, ref byte Ver_Test, ref byte Ver_Customer)
	{
		byte[] buffer = new byte[9] { 0, 128, 0, 0, 0, 0, 0, 0, 0 };
		m_HIDManager.WriteFeature(buffer);
		Thread.Sleep(1);
		byte[] array = new byte[9];
		m_HIDManager.GetFeature(array);
		Thread.Sleep(1);
		Ver_High = array[2];
		Ver_Low = array[3];
		Ver_Test = array[4];
		Ver_Customer = array[5];
		return true;
	}
}
