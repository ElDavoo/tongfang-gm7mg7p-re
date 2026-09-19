using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Linq;
using System.Runtime.InteropServices;
using System.Threading;
using System.Threading.Tasks;
using Microsoft.Win32;
using MyECIO;
using Utility;

namespace MyControlCenter;

internal class NvramVariable
{
	private static MyEcCtrl EcCtrl = MyEcCtrl.Instance;

	private static string m_ClassName = "NvramVariable";

	public static int m_projectID = 0;

	public static int m_supportLightBar = 0;

	public static int m_supportRGBLB = 0;

	public static int m_supportSingleColorKeyboard = 0;

	public static int m_supportCustomerList = 0;

	public static int m_switchColorCalibration = 1;

	public static int m_supportColorCalibration = 255;

	private static int m_SingleColorKeyboardDetection = 0;

	private static readonly int NVRAM_STRUCT_SIZE = Marshal.SizeOf(typeof(NVRAM_STRUCT));

	private static object NvramLock = new object();

	private static Dictionary<string, byte> FwVarsByteBuffer = new Dictionary<string, byte>();

	private static Dictionary<string, ushort> FwVarsUnit16Buffer = new Dictionary<string, ushort>();

	private static Dictionary<string, uint> FwVarsUnit32Buffer = new Dictionary<string, uint>();

	private static NVRAM_STRUCT _fwvars;

	private static int writeDelayTime = 3000;

	private static SemaphoreSlim semaphoreSlim = new SemaphoreSlim(1, 1);

	private Stopwatch stopwatch = new Stopwatch();

	private static dynamic LastCommand;

	public static string m_sLightbarType = "2";

	[DllImport("UEFI_Firmware.dll", CallingConvention = CallingConvention.Cdecl)]
	public static extern IntPtr ReadUefi(int startAddr, int endAddr);

	[DllImport("UEFI_Firmware.dll", CallingConvention = CallingConvention.Cdecl)]
	public static extern void WriteUefi(int startAddr, int endAddr, byte[] buffer);

	public static void SetFwVarsBuf<T>(string varname, T value)
	{
		if (typeof(T) == typeof(byte))
		{
			if (FwVarsByteBuffer.ContainsKey(varname))
			{
				FwVarsByteBuffer[varname] = Convert.ToByte(value);
			}
			else
			{
				FwVarsByteBuffer.Add(varname, Convert.ToByte(value));
			}
		}
		else if (typeof(T) == typeof(ushort))
		{
			if (FwVarsUnit16Buffer.ContainsKey(varname))
			{
				FwVarsUnit16Buffer[varname] = Convert.ToUInt16(value);
			}
			else
			{
				FwVarsUnit16Buffer.Add(varname, Convert.ToUInt16(value));
			}
		}
		else if (typeof(T) == typeof(uint))
		{
			if (FwVarsUnit32Buffer.ContainsKey(varname))
			{
				FwVarsUnit32Buffer[varname] = Convert.ToUInt32(value);
			}
			else
			{
				FwVarsUnit32Buffer.Add(varname, Convert.ToUInt32(value));
			}
		}
	}

	public static void UpdateBufToFwVars()
	{
		LogCtrl.Write("Update fw vars start FwVarsByteBuffer:" + FwVarsByteBuffer.Count() + "FwVarsUnit16Buffer:" + FwVarsUnit16Buffer.Count());
		foreach (KeyValuePair<string, byte> item in FwVarsByteBuffer)
		{
			LogCtrl.Write("Update fw vars " + item.Key + " " + item.Value);
			SetFwVars(item.Key, item.Value);
		}
		foreach (KeyValuePair<string, ushort> item2 in FwVarsUnit16Buffer)
		{
			LogCtrl.Write("Update fw vars " + item2.Key + " " + item2.Value);
			SetFwVars(item2.Key, item2.Value);
		}
		foreach (KeyValuePair<string, uint> item3 in FwVarsUnit32Buffer)
		{
			LogCtrl.Write("Update fw vars " + item3.Key + " " + item3.Value);
			SetFwVars(item3.Key, item3.Value);
		}
	}

	public static NVRAM_STRUCT GetFwVars()
	{
		try
		{
			writeDelayTime = (int)RegistryCtrl.RegistrySoftwareKeyRead(RegistryHive.LocalMachine, "\\OEM\\GamingCenter2\\Support", "NvramVariableTime", 3000);
			if (writeDelayTime == 3000)
			{
				RegistryCtrl.RegistrySoftwareKeyWrite(RegistryHive.LocalMachine, "\\OEM\\GamingCenter2\\Support", "NvramVariableTime", writeDelayTime, RegistryValueKind.DWord);
			}
		}
		catch (Exception)
		{
		}
		NVRAM_STRUCT nVRAM_STRUCT = default(NVRAM_STRUCT);
		if (Monitor.TryEnter(NvramLock, 100))
		{
			try
			{
				nVRAM_STRUCT = (NVRAM_STRUCT)Marshal.PtrToStructure(ReadUefi(0, NVRAM_STRUCT_SIZE), typeof(NVRAM_STRUCT));
			}
			catch (Exception ex2)
			{
				LogCtrl.TraceMessage("exception : " + ex2, "GetFwVars", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\Customize\\NvramVariable.cs", 440);
			}
			finally
			{
				Monitor.Exit(NvramLock);
			}
		}
		_fwvars = nVRAM_STRUCT;
		return nVRAM_STRUCT;
	}

	private static async void SetFwBufferTesting(string varname)
	{
		if (semaphoreSlim.CurrentCount == 0)
		{
			LastCommand = new
			{
				name = varname
			};
			return;
		}
		await semaphoreSlim.WaitAsync();
		try
		{
			int num = Marshal.SizeOf(typeof(NVRAM_STRUCT));
			byte[] array = new byte[num];
			IntPtr intPtr = Marshal.AllocHGlobal(num);
			Marshal.StructureToPtr(_fwvars, intPtr, fDeleteOld: true);
			Marshal.Copy(intPtr, array, 0, num);
			Marshal.FreeHGlobal(intPtr);
			WriteUefi(0, NVRAM_STRUCT_SIZE, array);
			await Task.Delay(writeDelayTime);
		}
		catch (Exception ex)
		{
			LogCtrl.TraceMessage("exception : " + ex, "SetFwBufferTesting", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\Customize\\NvramVariable.cs", 489);
		}
		finally
		{
			semaphoreSlim.Release();
			if (LastCommand != null)
			{
				NvramVariable.SetFwBufferTesting(LastCommand.name);
				LastCommand = null;
			}
			GC.Collect();
		}
	}

	public static void SetFwVars(string varname, byte[] value)
	{
		switch (varname)
		{
		case "RGBKeyboard08":
			_fwvars.RGBKeyboard08 = value;
			break;
		case "RGBKeyboard1A":
			_fwvars.RGBKeyboard1A = value;
			break;
		case "SmartLightbar08":
			_fwvars.SmartLightbar08 = value;
			break;
		case "SmartLightbar1A":
			_fwvars.SmartLightbar1A = value;
			break;
		}
		SetFwBufferTesting(varname);
	}

	private static byte[] getBytes(NVRAM_STRUCT str)
	{
		int num = Marshal.SizeOf(str);
		byte[] array = new byte[num];
		IntPtr intPtr = Marshal.AllocHGlobal(num);
		Marshal.StructureToPtr(str, intPtr, fDeleteOld: true);
		Marshal.Copy(intPtr, array, 0, num);
		Marshal.FreeHGlobal(intPtr);
		return array;
	}

	public static void SetFwVars(string varname, byte value)
	{
		switch (varname)
		{
		case "PowerMode":
			_fwvars.PowerMode = value;
			break;
		case "MemoryOverClockSwitch":
			_fwvars.MemoryOverClockSwitch = value;
			break;
		case "ApExistFlag":
			_fwvars.ApExistFlag = value;
			break;
		case "OverClockRecoveryFlag":
			_fwvars.OverClockRecoveryFlag = value;
			break;
		case "ACRecoveryStatus":
			_fwvars.ACRecoveryStatus = value;
			break;
		case "ApUseFlag":
			_fwvars.ApUseFlag = value;
			break;
		case "OemDisplayMode":
			_fwvars.OemDisplayMode = value;
			break;
		case "FnKeyStatus":
			_fwvars.FnKeyStatus = value;
			break;
		}
		SetFwBufferTesting(varname);
		LogCtrl.TraceMessage("varname: " + varname + ", value: " + value.ToString("X2"), "SetFwVars", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\Customize\\NvramVariable.cs", 666);
	}

	public static void SetFwVars(string varname, ushort value)
	{
		switch (varname)
		{
		case "ICpuCoreVoltageValue":
			_fwvars.ICpuCoreVoltageValue = value;
			break;
		case "ICpuCoreVoltageOffsetValue":
			_fwvars.ICpuCoreVoltageOffsetValue = value;
			break;
		case "ICpuCoreVoltageOffsetNegativeValue":
			_fwvars.ICpuCoreVoltageOffsetNegativeValue = value;
			break;
		case "ICpuTauValue":
			_fwvars.ICpuTauValue = value;
			break;
		}
		SetFwBufferTesting(varname);
		LogCtrl.TraceMessage("varname: " + varname + ", value: " + value.ToString("X"), "SetFwVars", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\Customize\\NvramVariable.cs", 717);
	}

	public static void SetFwVars(string varname, uint value)
	{
		if (!(varname == "ACpuFreqValue"))
		{
			if (varname == "ACpuVoltageValue")
			{
				_fwvars.ACpuVoltageValue = value;
			}
		}
		else
		{
			_fwvars.ACpuFreqValue = value;
		}
		SetFwBufferTesting(varname);
		LogCtrl.TraceMessage("varname: " + varname + ", value: " + value.ToString("X"), "SetFwVars", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\Customize\\NvramVariable.cs", 762);
	}

	public static void SetFwVars_RGBLightbar(byte _mode, byte _red, byte _green, byte _blue)
	{
		_fwvars.RGBLightbarMode = _mode;
		_fwvars.RGBLightbarMode_R = _red;
		_fwvars.RGBLightbarMode_G = _green;
		_fwvars.RGBLightbarMode_B = _blue;
		SetFwBufferTesting(_mode.ToString());
		LogCtrl.TraceMessage("RGBLightbarMode: " + _mode.ToString("X2") + ", RGBLightbarMode_R: " + _red.ToString("X2") + ", RGBLightbarMode_G: " + _green.ToString("X2") + ", RGBLightbarMode_B: " + _blue.ToString("X2"), "SetFwVars_RGBLightbar", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\Customize\\NvramVariable.cs", 801);
	}

	public static void Get()
	{
		m_projectID = EcCtrl.GetProjectIdFromEC();
		try
		{
			NVRAM_STRUCT fwVars = GetFwVars();
			LogCtrl.TraceMessage(fwVars.ToIndentedJsonString(), "Get", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\Customize\\NvramVariable.cs", 825);
			byte[] bytes = BitConverter.GetBytes(fwVars.SupportByte);
			_ = bytes[0];
			int num = bytes[0] >> 4;
			_ = bytes[1];
			_ = bytes[1];
			m_supportLightBar = (((num & 4) == 4) ? 1 : 0);
			LogCtrl.Write($"NvramVariable  [Get] ProjectID[{m_projectID}], BL[{m_supportLightBar}], CustomerList[{m_supportCustomerList}]");
			RegistryCtrl.RegistrySoftwareKeyWrite(RegistryHive.LocalMachine, "\\OEM\\GamingCenter2\\Support", "LightBar", m_supportLightBar, RegistryValueKind.DWord);
			RegistryCtrl.RegistrySoftwareKeyWrite(RegistryHive.LocalMachine, "\\OEM\\GamingCenter2\\Support", "supportCustomerList", m_supportCustomerList, RegistryValueKind.DWord);
		}
		catch (Exception ex)
		{
			LogCtrl.Write($"NvramVariable  [Get] Read NvramVariables Support Data Failed {ex.ToString()}");
		}
		if (EcCtrl.isSupportRGBLBFromEC() == 1)
		{
			m_supportRGBLB = 1;
		}
		else
		{
			m_supportRGBLB = isSupportRGBLB(m_projectID);
		}
		RegistryCtrl.RegistrySoftwareKeyWrite(RegistryHive.LocalMachine, "\\OEM\\GamingCenter2\\Support", "RGBLB", m_supportRGBLB, RegistryValueKind.DWord);
		m_SingleColorKeyboardDetection = IsSingleColorKeyboardDetection();
		RegistryCtrl.RegistrySoftwareKeyWrite(RegistryHive.LocalMachine, "\\OEM\\GamingCenter2\\Support", "SingleColorKeyboardDetection", m_SingleColorKeyboardDetection, RegistryValueKind.DWord);
		if (m_SingleColorKeyboardDetection == 1)
		{
			m_supportSingleColorKeyboard = isSupportSingleColorKeyboardFromEC();
		}
		else
		{
			m_supportSingleColorKeyboard = 0;
		}
		RegistryCtrl.RegistrySoftwareKeyWrite(RegistryHive.LocalMachine, "\\OEM\\GamingCenter2\\Support", "SingleColorKeyboard", m_supportSingleColorKeyboard, RegistryValueKind.DWord);
		LogCtrl.Write($"NvramVariable  [Get] SingleColorKeyboardDetection[{m_SingleColorKeyboardDetection}], SingleColorKeyboard[{m_supportSingleColorKeyboard}]");
		m_switchColorCalibration = (int)RegistryCtrl.RegistrySoftwareKeyRead(RegistryHive.LocalMachine, "\\OEM\\GamingCenter2", "ColorCalibration", 1);
		if (m_switchColorCalibration == 0)
		{
			m_supportColorCalibration = 0;
		}
		else
		{
			m_supportColorCalibration = isSupportColorCalibration(m_projectID);
		}
		RegistryCtrl.RegistrySoftwareKeyWrite(RegistryHive.LocalMachine, "\\OEM\\GamingCenter2\\Support", "ColorCalibration", m_supportColorCalibration, RegistryValueKind.DWord);
		LogCtrl.Write("NvramVariable  [Get] End");
	}

	public static List<string[]> GetKeyboardWelcomeEffect()
	{
		List<string[]> list = new List<string[]>();
		NVRAM_STRUCT fwVars = GetFwVars();
		LogCtrl.TraceMessage("RGBKeyboard08: 0x" + BitConverter.ToString(fwVars.RGBKeyboard08).Replace("-", ","), "GetKeyboardWelcomeEffect", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\Customize\\NvramVariable.cs", 908);
		LogCtrl.TraceMessage("RGBKeyboard1A: 0x" + BitConverter.ToString(fwVars.RGBKeyboard1A).Replace("-", ","), "GetKeyboardWelcomeEffect", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\Customize\\NvramVariable.cs", 909);
		string[] item = fwVars.RGBKeyboard08.Select((byte byteValue) => byteValue.ToString("X2")).ToArray();
		string[] item2 = fwVars.RGBKeyboard1A.Select((byte byteValue) => byteValue.ToString("X2")).ToArray();
		list.Add(item);
		list.Add(item2);
		return list;
	}

	public static List<string[]> GetLightbarWelcomeEffect()
	{
		List<string[]> list = new List<string[]>();
		NVRAM_STRUCT fwVars = GetFwVars();
		LogCtrl.TraceMessage("SmartLightbar08: " + BitConverter.ToString(fwVars.SmartLightbar08).Replace("-", ","), "GetLightbarWelcomeEffect", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\Customize\\NvramVariable.cs", 926);
		LogCtrl.TraceMessage("SmartLightbar1A: " + BitConverter.ToString(fwVars.SmartLightbar1A).Replace("-", ","), "GetLightbarWelcomeEffect", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\Customize\\NvramVariable.cs", 927);
		string[] item = fwVars.SmartLightbar08.Select((byte byteValue) => byteValue.ToString("X2")).ToArray();
		string[] item2 = fwVars.SmartLightbar1A.Select((byte byteValue) => byteValue.ToString("X2")).ToArray();
		list.Add(item);
		list.Add(item2);
		return list;
	}

	private static int isSupportRGBLB(int projectID)
	{
		int num = 255;
		int num2 = 0;
		int num3 = 0;
		int num4 = 0;
		if (projectID >= 3)
		{
			try
			{
				NVRAM_STRUCT fwVars = GetFwVars();
				num = fwVars.RGBLightbarMode;
				num2 = fwVars.RGBLightbarMode_R;
				num3 = fwVars.RGBLightbarMode_G;
				num4 = fwVars.RGBLightbarMode_B;
				LogCtrl.Write($"NvramVariable  [Get] RGBLB[{num}], R[{num2}], G[{num3}], B[{num4}]");
			}
			catch (Exception ex)
			{
				LogCtrl.Write($"NvramVariable  [Get] Read OemService RGBLB Support Data Failed {ex.ToString()}");
			}
		}
		else
		{
			num = 255;
		}
		return num;
	}

	private static int isSupportColorCalibration(int projectID)
	{
		NVRAM_STRUCT fwVars = GetFwVars();
		LogCtrl.Write($"NvramVariable  [Get] ColorCalibration[{fwVars.ColorCalibrationSupport}]");
		return fwVars.ColorCalibrationSupport;
	}

	public static int IsSingleColorKeyboardDetection()
	{
		bool flag = m_projectID.IsProjectId_SingleColorKeyboard();
		if (flag)
		{
			LogCtrl.Write("NvramVariable  [Get] SingleColorKeyboardProjectIDs, IsCommercialPlatform | " + flag);
			return 1;
		}
		return 0;
	}

	private static int isSupportSingleColorKeyboardFromEC()
	{
		byte Data = 0;
		EcCtrl.Read(m_ClassName, 1932, ref Data);
		if ((byte)(Convert.ToUInt64(Data) & 1) == 1)
		{
			LogCtrl.Write("NvramVariable  [Get] isSupportSingleColorKeyboard | true");
			return 1;
		}
		LogCtrl.Write("NvramVariable  [Get] isSupportSingleColorKeyboard | false");
		return 0;
	}

	public static void LoadRegistryFromSupport()
	{
		string subKey = "\\OEM\\GamingCenter2\\Support";
		try
		{
			int supportLightBar = (int)RegistryCtrl.RegistrySoftwareKeyRead(RegistryHive.LocalMachine, subKey, "LightBar", 9u);
			int supportRGBLB = (int)RegistryCtrl.RegistrySoftwareKeyRead(RegistryHive.LocalMachine, subKey, "RGBLB", 9u);
			m_supportLightBar = supportLightBar;
			m_supportRGBLB = supportRGBLB;
		}
		catch
		{
			LogCtrl.Write("[LoadRegistryFromSupport] failed.");
		}
	}

	public static string GetLightbarSupportType()
	{
		if (m_sLightbarType != "3")
		{
			if (m_supportLightBar == 0)
			{
				m_sLightbarType = "0";
			}
			else if (m_supportLightBar == 1 && m_supportRGBLB == 255)
			{
				m_sLightbarType = "1";
			}
			if (m_supportRGBLB == 1)
			{
				m_sLightbarType = "2";
			}
		}
		return m_sLightbarType;
	}

	public static string GetKeyboardType()
	{
		string text = "1";
		if (m_SingleColorKeyboardDetection == 1)
		{
			if (m_supportSingleColorKeyboard == 1)
			{
				return "2";
			}
			return "0";
		}
		return "1";
	}
}
