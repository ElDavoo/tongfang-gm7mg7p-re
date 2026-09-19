using System;
using System.Runtime.InteropServices;
using Newtonsoft.Json;

namespace MyControlCenter;

public struct NVRAM_STRUCT
{
	[JsonConverter(typeof(HexStringJsonConverter))]
	public uint OemBoardSsid;

	[JsonConverter(typeof(HexStringJsonConverter))]
	public ushort SupportByte;

	[JsonConverter(typeof(HexStringJsonConverter))]
	public byte ProjectID;

	[JsonConverter(typeof(HexStringJsonConverter))]
	public byte KeyboardType;

	[JsonConverter(typeof(HexStringJsonConverter))]
	public byte CustomerList;

	[JsonConverter(typeof(HexStringJsonConverter))]
	public byte RGBLightbarMode;

	[JsonConverter(typeof(HexStringJsonConverter))]
	public byte RGBLightbarMode_R;

	[JsonConverter(typeof(HexStringJsonConverter))]
	public byte RGBLightbarMode_G;

	[JsonConverter(typeof(HexStringJsonConverter))]
	public byte RGBLightbarMode_B;

	[JsonConverter(typeof(HexStringJsonConverter))]
	public byte ColorCalibrationSupport;

	[JsonConverter(typeof(HexStringJsonConverter))]
	public byte TDRdata;

	[MarshalAs(UnmanagedType.ByValArray, SizeConst = 8)]
	[JsonConverter(typeof(ByteArrayHexConverter))]
	public byte[] RGBKeyboard1A;

	[MarshalAs(UnmanagedType.ByValArray, SizeConst = 8)]
	[JsonConverter(typeof(ByteArrayHexConverter))]
	public byte[] RGBKeyboard08;

	[MarshalAs(UnmanagedType.ByValArray, SizeConst = 8)]
	[JsonConverter(typeof(ByteArrayHexConverter))]
	public byte[] SmartLightbar1A;

	[MarshalAs(UnmanagedType.ByValArray, SizeConst = 8)]
	[JsonConverter(typeof(ByteArrayHexConverter))]
	public byte[] SmartLightbar08;

	[JsonConverter(typeof(HexStringJsonConverter))]
	public byte PowerMode;

	[JsonConverter(typeof(HexStringJsonConverter))]
	public byte BatteryLimitation;

	[JsonConverter(typeof(HexStringJsonConverter))]
	public byte ChargeMaximumLimit;

	[JsonConverter(typeof(HexStringJsonConverter))]
	public byte ChargeMinimumLimit;

	[JsonConverter(typeof(HexStringJsonConverter))]
	public byte MemoryOverClockSwitch;

	[JsonConverter(typeof(HexStringJsonConverter))]
	public ushort ICpuCoreVoltageValue;

	[JsonConverter(typeof(HexStringJsonConverter))]
	public ushort ICpuCoreVoltageMaximum;

	[JsonConverter(typeof(HexStringJsonConverter))]
	public ushort ICpuCoreVoltageMinimum;

	[JsonConverter(typeof(HexStringJsonConverter))]
	public ushort ICpuCoreVoltageOffsetValue;

	[JsonConverter(typeof(HexStringJsonConverter))]
	public ushort ICpuCoreVoltageOffsetMaximum;

	[JsonConverter(typeof(HexStringJsonConverter))]
	public ushort ICpuCoreVoltageOffsetMinimum;

	[JsonConverter(typeof(HexStringJsonConverter))]
	public ushort ICpuTauValue;

	[JsonConverter(typeof(HexStringJsonConverter))]
	public byte ACpuOverClockSupport;

	[JsonConverter(typeof(HexStringJsonConverter))]
	public uint ACpuFreqValue;

	[JsonConverter(typeof(HexStringJsonConverter))]
	public uint ACpuFreqValueMaximum;

	[JsonConverter(typeof(HexStringJsonConverter))]
	public uint ACpuFreqValueMinimum;

	[JsonConverter(typeof(HexStringJsonConverter))]
	public uint ACpuVoltageValue;

	[JsonConverter(typeof(HexStringJsonConverter))]
	public uint ACpuVoltageValueMaximum;

	[JsonConverter(typeof(HexStringJsonConverter))]
	public uint ACpuVoltageValueMinimum;

	[JsonConverter(typeof(HexStringJsonConverter))]
	public byte OverClockRecoveryFlag;

	[JsonConverter(typeof(HexStringJsonConverter))]
	public byte ApExistFlag;

	[JsonConverter(typeof(HexStringJsonConverter))]
	public byte ACRecoverySupport;

	[JsonConverter(typeof(HexStringJsonConverter))]
	public byte ACRecoveryStatus;

	[JsonConverter(typeof(HexStringJsonConverter))]
	public byte MemoryOverClockSupport;

	[JsonConverter(typeof(HexStringJsonConverter))]
	public byte ApUseFlag;

	[JsonConverter(typeof(HexStringJsonConverter))]
	public byte OemDisplayMode;

	[JsonConverter(typeof(HexStringJsonConverter))]
	public ushort ICpuCoreVoltageOffsetNegativeValue;

	[JsonConverter(typeof(HexStringJsonConverter))]
	public byte ICpuCoreVoltageOffsetRangeType;

	[JsonConverter(typeof(HexStringJsonConverter))]
	public byte FnKeyStatus;

	[MarshalAs(UnmanagedType.ByValArray, SizeConst = 76)]
	[JsonConverter(typeof(ByteArrayHexConverter))]
	public byte[] Reserved;

	public override string ToString()
	{
		return "OemBoardSsid: 0x" + OemBoardSsid.ToString("X") + ", SupportByte: 0x" + SupportByte.ToString("X") + ", ProjectID: 0x" + ProjectID.ToString("X2") + ", KeyboardType: 0x" + KeyboardType.ToString("X2") + ", CustomerList: 0x" + CustomerList.ToString("X2") + ", RGBLightbarMode: 0x" + RGBLightbarMode.ToString("X2") + ", RGBLightbarMode_R: 0x" + RGBLightbarMode_R.ToString("X2") + ", RGBLightbarMode_G: 0x" + RGBLightbarMode_G.ToString("X2") + ", RGBLightbarMode_B: 0x" + RGBLightbarMode_B.ToString("X2") + ", ColorCalibrationSupport: 0x" + ColorCalibrationSupport.ToString("X2") + ", TDRdata: 0x" + TDRdata.ToString("X2") + ", RGBKeyboard1A: 0x" + BitConverter.ToString(RGBKeyboard1A).Replace("-", ",") + ", RGBKeyboard08: 0x" + BitConverter.ToString(RGBKeyboard08).Replace("-", ",") + ", SmartLightbar1A: 0x" + BitConverter.ToString(SmartLightbar1A).Replace("-", ",") + ", SmartLightbar08: 0x" + BitConverter.ToString(SmartLightbar08).Replace("-", ",") + ", PowerMode: 0x" + PowerMode.ToString("X2") + ", BatteryLimitation: 0x" + BatteryLimitation.ToString("X2") + ", ChargeMaximumLimit: 0x" + ChargeMaximumLimit.ToString("X2") + ", ChargeMinimumLimit: 0x" + ChargeMinimumLimit.ToString("X2") + ", MemoryOverClockSwitch: 0x" + MemoryOverClockSwitch.ToString("X2") + ", ICpuCoreVoltageValue: 0x" + ICpuCoreVoltageValue.ToString("X") + ", ICpuCoreVoltageMaximum: 0x" + ICpuCoreVoltageMaximum.ToString("X") + ", ICpuCoreVoltageMinimum: 0x" + ICpuCoreVoltageMinimum.ToString("X") + ", ICpuCoreVoltageOffsetValue: 0x" + ICpuCoreVoltageOffsetValue.ToString("X") + ", ICpuCoreVoltageOffsetMaximum: 0x" + ICpuCoreVoltageOffsetMaximum.ToString("X") + ", ICpuCoreVoltageOffsetMinimum: 0x" + ICpuCoreVoltageOffsetMinimum.ToString("X") + ", ICpuTauValue: 0x" + ICpuTauValue.ToString("X") + ", ACpuOverClockSupport: 0x" + ACpuOverClockSupport.ToString("X2") + ", ACpuFreqValue: 0x" + ACpuFreqValue.ToString("X") + ", ACpuFreqValueMaximum: 0x" + ACpuFreqValueMaximum.ToString("X") + ", ACpuFreqValueMinimum: 0x" + ACpuFreqValueMinimum.ToString("X") + ", ACpuVoltageValue: 0x" + ACpuVoltageValue.ToString("X") + ", ACpuVoltageValueMaximum: 0x" + ACpuVoltageValueMaximum.ToString("X") + ", ACpuVoltageValueMinimum: 0x" + ACpuVoltageValueMinimum.ToString("X") + ", OverClockRecoveryFlag: 0x" + OverClockRecoveryFlag.ToString("X2") + ", ApExistFlag: 0x" + ApExistFlag.ToString("X2") + ", ACRecoverySupport: 0x" + ACRecoverySupport.ToString("X2") + ", ACRecoveryStatus: 0x" + ACRecoveryStatus.ToString("X2") + ", MemoryOverClockSupport: 0x" + MemoryOverClockSupport.ToString("X2") + ", ApUseFlag: 0x" + ApUseFlag.ToString("X2") + ", OemDisplayMode: 0x" + OemDisplayMode.ToString("X2") + ", ICpuCoreVoltageOffsetNegativeValue: 0x" + ICpuCoreVoltageOffsetNegativeValue.ToString("X") + ", ICpuCoreVoltageOffsetRangeType: 0x" + ICpuCoreVoltageOffsetRangeType.ToString("X2") + ", FnKeyStatus: 0x" + FnKeyStatus.ToString("X2");
	}

	public string ToHexBufferString()
	{
		int num = Marshal.SizeOf(typeof(NVRAM_STRUCT));
		byte[] destination = new byte[num];
		IntPtr intPtr = Marshal.AllocHGlobal(num);
		Marshal.StructureToPtr(this, intPtr, fDeleteOld: true);
		Marshal.Copy(intPtr, destination, 0, num);
		Marshal.FreeHGlobal(intPtr);
		return "";
	}

	public string ToIndentedJsonString()
	{
		return JsonConvert.SerializeObject(this, Formatting.Indented);
	}
}
