using System;
using System.Collections.Generic;
using System.IO;
using System.Management;
using System.Text;

namespace MyControlCenter.MySetting.ColorCalibration;

internal class SMBIOS
{
	public class Structure
	{
		private readonly byte type;

		private readonly ushort handle;

		private readonly byte[] data;

		private readonly string[] strings;

		public byte Type => type;

		public ushort Handle => handle;

		protected int GetByte(int offset)
		{
			if (offset < data.Length && offset >= 0)
			{
				return data[offset];
			}
			return 0;
		}

		protected int GetWord(int offset)
		{
			if (offset + 1 < data.Length && offset >= 0)
			{
				return (data[offset + 1] << 8) | data[offset];
			}
			return 0;
		}

		protected string GetString(int offset)
		{
			if (offset < data.Length && data[offset] > 0 && data[offset] <= strings.Length)
			{
				return strings[data[offset] - 1];
			}
			return "";
		}

		public Structure(byte type, ushort handle, byte[] data, string[] strings)
		{
			this.type = type;
			this.handle = handle;
			this.data = data;
			this.strings = strings;
		}
	}

	public class BIOSInformation : Structure
	{
		private readonly string vendor;

		private readonly string version;

		private readonly string date;

		public string Vendor => vendor;

		public string Version => version;

		public string Date => date;

		public BIOSInformation(string vendor, string version, string date)
			: base(0, 0, null, null)
		{
			this.vendor = vendor;
			this.version = version;
			this.date = date;
		}

		public BIOSInformation(byte type, ushort handle, byte[] data, string[] strings)
			: base(type, handle, data, strings)
		{
			vendor = GetString(4);
			version = GetString(5);
			date = GetString(8);
		}
	}

	public class SystemInformation : Structure
	{
		private readonly string manufacturerName;

		private readonly string productName;

		private readonly string version;

		private readonly string serialNumber;

		private readonly string family;

		public string ManufacturerName => manufacturerName;

		public string ProductName => productName;

		public string Version => version;

		public string SerialNumber => serialNumber;

		public string Family => family;

		public SystemInformation(string manufacturerName, string productName, string version, string serialNumber, string family)
			: base(1, 0, null, null)
		{
			this.manufacturerName = manufacturerName;
			this.productName = productName;
			this.version = version;
			this.serialNumber = serialNumber;
			this.family = family;
		}

		public SystemInformation(byte type, ushort handle, byte[] data, string[] strings)
			: base(type, handle, data, strings)
		{
			manufacturerName = GetString(4);
			productName = GetString(5);
			version = GetString(6);
			serialNumber = GetString(7);
			family = GetString(26);
		}
	}

	public class BaseBoardInformation : Structure
	{
		private readonly string manufacturerName;

		private readonly string productName;

		private readonly string version;

		private readonly string serialNumber;

		public string ManufacturerName => manufacturerName;

		public string ProductName => productName;

		public string Version => version;

		public string SerialNumber => serialNumber;

		public BaseBoardInformation(string manufacturerName, string productName, string version, string serialNumber)
			: base(2, 0, null, null)
		{
			this.manufacturerName = manufacturerName;
			this.productName = productName;
			this.version = version;
			this.serialNumber = serialNumber;
		}

		public BaseBoardInformation(byte type, ushort handle, byte[] data, string[] strings)
			: base(type, handle, data, strings)
		{
			manufacturerName = GetString(4).Trim();
			productName = GetString(5).Trim();
			version = GetString(6).Trim();
			serialNumber = GetString(7).Trim();
		}
	}

	public class ProcessorInformation : Structure
	{
		public string ManufacturerName { get; private set; }

		public string Version { get; private set; }

		public int CoreCount { get; private set; }

		public int CoreEnabled { get; private set; }

		public int ThreadCount { get; private set; }

		public int ExternalClock { get; private set; }

		public ProcessorInformation(byte type, ushort handle, byte[] data, string[] strings)
			: base(type, handle, data, strings)
		{
			ManufacturerName = GetString(7).Trim();
			Version = GetString(16).Trim();
			CoreCount = GetByte(35);
			CoreEnabled = GetByte(36);
			ThreadCount = GetByte(37);
			ExternalClock = GetWord(18);
		}
	}

	public class MemoryDevice : Structure
	{
		private readonly string deviceLocator;

		private readonly string bankLocator;

		private readonly string manufacturerName;

		private readonly string serialNumber;

		private readonly string partNumber;

		private readonly int speed;

		private readonly int size;

		private readonly int type;

		public string DeviceLocator => deviceLocator;

		public string BankLocator => bankLocator;

		public string ManufacturerName => manufacturerName;

		public string SerialNumber => serialNumber;

		public string PartNumber => partNumber;

		public int Speed => speed;

		public int Size => size;

		public string MemoryType => ParseMemoryType(type);

		public MemoryDevice(byte type, ushort handle, byte[] data, string[] strings)
			: base(type, handle, data, strings)
		{
			size = GetWord(12);
			deviceLocator = GetString(16).Trim();
			bankLocator = GetString(17).Trim();
			this.type = GetByte(18);
			manufacturerName = GetString(23).Trim();
			serialNumber = GetString(24).Trim();
			partNumber = GetString(26).Trim();
			speed = GetWord(21);
		}

		public string ParseMemoryType(int type)
		{
			string text = "";
			switch (type)
			{
			case 1:
				return "Other";
			case 2:
				return "Unknown";
			case 3:
				return "DRAM";
			case 4:
				return "EDRAM";
			case 5:
				return "VRAM ";
			case 6:
				return "SRAM ";
			case 7:
				return "RAM";
			case 8:
				return "ROM";
			case 9:
				return "FLASH";
			case 10:
				return "EEPROM";
			case 11:
				return "FEPROM";
			case 12:
				return "EPROM";
			case 13:
				return "CDRAM";
			case 14:
				return "3DRAM";
			case 15:
				return "SDRAM";
			case 16:
				return "SGRAM";
			case 17:
				return "RDRAM";
			case 18:
				return "DDR";
			case 19:
				return "DDR2";
			case 20:
				return "DDR2 FB-DIMM ";
			case 21:
			case 22:
			case 23:
				return "Reserved";
			case 24:
				return "DDR3";
			case 25:
				return "FBD2";
			case 26:
				return "DDR4";
			case 27:
				return "LPDDR";
			case 28:
				return "LPDDR2";
			case 29:
				return "LPDDR3";
			case 30:
				return "LPDDR4";
			default:
				return "Unknown";
			}
		}
	}

	private readonly byte[] raw;

	private readonly Structure[] table;

	private readonly Version version;

	private readonly BIOSInformation biosInformation;

	private readonly SystemInformation systemInformation;

	private readonly BaseBoardInformation baseBoardInformation;

	private readonly ProcessorInformation processorInformation;

	private readonly MemoryDevice[] memoryDevices;

	public BIOSInformation BIOS => biosInformation;

	public SystemInformation System => systemInformation;

	public BaseBoardInformation Board => baseBoardInformation;

	public ProcessorInformation Processor => processorInformation;

	public MemoryDevice[] MemoryDevices => memoryDevices;

	private static string ReadSysFS(string path)
	{
		try
		{
			if (File.Exists(path))
			{
				using (StreamReader streamReader = new StreamReader(path))
				{
					return streamReader.ReadLine();
				}
			}
			return null;
		}
		catch
		{
			return null;
		}
	}

	public string[] GetLogicalDrives(int driveIndex)
	{
		List<string> list = new List<string>();
		try
		{
			using ManagementObjectSearcher managementObjectSearcher = new ManagementObjectSearcher("root\\CIMV2", "SELECT * FROM Win32_DiskPartition WHERE DiskIndex = " + driveIndex);
			using ManagementObjectCollection managementObjectCollection = managementObjectSearcher.Get();
			foreach (ManagementObject item in managementObjectCollection)
			{
				using ManagementObjectCollection managementObjectCollection2 = item.GetRelated("Win32_LogicalDisk");
				foreach (ManagementBaseObject item2 in managementObjectCollection2)
				{
					list.Add(((string)item2["Name"]).TrimEnd(':'));
				}
			}
		}
		catch (Exception arg)
		{
			Console.WriteLine($"GetLogicalDrives error {arg}");
		}
		return list.ToArray();
	}

	public SMBIOS()
	{
		int platform = (int)Environment.OSVersion.Platform;
		if (platform == 4 || platform == 128)
		{
			raw = null;
			table = null;
			string manufacturerName = ReadSysFS("/sys/class/dmi/id/board_vendor");
			string productName = ReadSysFS("/sys/class/dmi/id/board_name");
			string text = ReadSysFS("/sys/class/dmi/id/board_version");
			baseBoardInformation = new BaseBoardInformation(manufacturerName, productName, text, null);
			string manufacturerName2 = ReadSysFS("/sys/class/dmi/id/sys_vendor");
			string productName2 = ReadSysFS("/sys/class/dmi/id/product_name");
			string text2 = ReadSysFS("/sys/class/dmi/id/product_version");
			systemInformation = new SystemInformation(manufacturerName2, productName2, text2, null, null);
			string vendor = ReadSysFS("/sys/class/dmi/id/bios_vendor");
			string text3 = ReadSysFS("/sys/class/dmi/id/bios_version");
			string date = ReadSysFS("/sys/class/dmi/id/bios_date");
			biosInformation = new BIOSInformation(vendor, text3, date);
			memoryDevices = new MemoryDevice[0];
			return;
		}
		List<Structure> list = new List<Structure>();
		List<MemoryDevice> list2 = new List<MemoryDevice>();
		raw = null;
		byte b = 0;
		byte b2 = 0;
		try
		{
			ManagementObjectCollection managementObjectCollection;
			using (ManagementObjectSearcher managementObjectSearcher = new ManagementObjectSearcher("root\\WMI", "SELECT * FROM MSSMBios_RawSMBiosTables"))
			{
				managementObjectCollection = managementObjectSearcher.Get();
			}
			using ManagementObjectCollection.ManagementObjectEnumerator managementObjectEnumerator = managementObjectCollection.GetEnumerator();
			if (managementObjectEnumerator.MoveNext())
			{
				ManagementObject managementObject = (ManagementObject)managementObjectEnumerator.Current;
				raw = (byte[])managementObject["SMBiosData"];
				b = (byte)managementObject["SmbiosMajorVersion"];
				b2 = (byte)managementObject["SmbiosMinorVersion"];
			}
		}
		catch (Exception arg)
		{
			Console.WriteLine("Get SMBIOS info failed {0}", arg);
		}
		if (b > 0 || b2 > 0)
		{
			version = new Version(b, b2);
		}
		if (raw != null && raw.Length != 0)
		{
			int num = 0;
			byte b3 = raw[num];
			while (num + 4 < raw.Length && b3 != 127)
			{
				b3 = raw[num];
				int num2 = raw[num + 1];
				ushort handle = (ushort)((raw[num + 2] << 8) | raw[num + 3]);
				if (num + num2 > raw.Length)
				{
					break;
				}
				byte[] array = new byte[num2];
				Array.Copy(raw, num, array, 0, num2);
				num += num2;
				List<string> list3 = new List<string>();
				if (num < raw.Length && raw[num] == 0)
				{
					num++;
				}
				while (num < raw.Length && raw[num] != 0)
				{
					StringBuilder stringBuilder = new StringBuilder();
					for (; num < raw.Length && raw[num] != 0; num++)
					{
						stringBuilder.Append((char)raw[num]);
					}
					num++;
					list3.Add(stringBuilder.ToString());
				}
				num++;
				switch (b3)
				{
				case 0:
					biosInformation = new BIOSInformation(b3, handle, array, list3.ToArray());
					list.Add(biosInformation);
					break;
				case 1:
					systemInformation = new SystemInformation(b3, handle, array, list3.ToArray());
					list.Add(systemInformation);
					break;
				case 2:
					baseBoardInformation = new BaseBoardInformation(b3, handle, array, list3.ToArray());
					list.Add(baseBoardInformation);
					break;
				case 4:
					processorInformation = new ProcessorInformation(b3, handle, array, list3.ToArray());
					list.Add(processorInformation);
					break;
				case 17:
				{
					MemoryDevice item = new MemoryDevice(b3, handle, array, list3.ToArray());
					list2.Add(item);
					list.Add(item);
					break;
				}
				default:
					list.Add(new Structure(b3, handle, array, list3.ToArray()));
					break;
				}
			}
		}
		memoryDevices = list2.ToArray();
		table = list.ToArray();
	}

	public string GetReport()
	{
		StringBuilder stringBuilder = new StringBuilder();
		if (version != null)
		{
			stringBuilder.Append("SMBIOS Version: ");
			stringBuilder.AppendLine(version.ToString(2));
			stringBuilder.AppendLine();
		}
		if (BIOS != null)
		{
			stringBuilder.Append("BIOS Vendor: ");
			stringBuilder.AppendLine(BIOS.Vendor);
			stringBuilder.Append("BIOS Version: ");
			stringBuilder.AppendLine(BIOS.Version);
			stringBuilder.Append("BIOS Release Date: ");
			stringBuilder.AppendLine(BIOS.Date);
			stringBuilder.AppendLine();
		}
		if (System != null)
		{
			stringBuilder.Append("System Manufacturer: ");
			stringBuilder.AppendLine(System.ManufacturerName);
			stringBuilder.Append("System Name: ");
			stringBuilder.AppendLine(System.ProductName);
			stringBuilder.Append("System Version: ");
			stringBuilder.AppendLine(System.Version);
			stringBuilder.AppendLine();
		}
		if (Board != null)
		{
			stringBuilder.Append("Mainboard Manufacturer: ");
			stringBuilder.AppendLine(Board.ManufacturerName);
			stringBuilder.Append("Mainboard Name: ");
			stringBuilder.AppendLine(Board.ProductName);
			stringBuilder.Append("Mainboard Version: ");
			stringBuilder.AppendLine(Board.Version);
			stringBuilder.AppendLine();
		}
		if (Processor != null)
		{
			stringBuilder.Append("Processor Manufacturer: ");
			stringBuilder.AppendLine(Processor.ManufacturerName);
			stringBuilder.Append("Processor Version: ");
			stringBuilder.AppendLine(Processor.Version);
			stringBuilder.Append("Processor Core Count: ");
			stringBuilder.AppendLine(Processor.CoreCount.ToString());
			stringBuilder.Append("Processor Core Enabled: ");
			stringBuilder.AppendLine(Processor.CoreEnabled.ToString());
			stringBuilder.Append("Processor Thread Count: ");
			stringBuilder.AppendLine(Processor.ThreadCount.ToString());
			stringBuilder.Append("Processor External Clock: ");
			stringBuilder.Append(Processor.ExternalClock);
			stringBuilder.AppendLine(" Mhz");
			stringBuilder.AppendLine();
		}
		for (int i = 0; i < MemoryDevices.Length; i++)
		{
			stringBuilder.Append("Memory Device [" + i + "] Manufacturer: ");
			stringBuilder.AppendLine(MemoryDevices[i].ManufacturerName);
			stringBuilder.Append("Memory Device [" + i + "] Part Number: ");
			stringBuilder.AppendLine(MemoryDevices[i].PartNumber);
			stringBuilder.Append("Memory Device [" + i + "] Device Locator: ");
			stringBuilder.AppendLine(MemoryDevices[i].DeviceLocator);
			stringBuilder.Append("Memory Device [" + i + "] Bank Locator: ");
			stringBuilder.AppendLine(MemoryDevices[i].BankLocator);
			stringBuilder.Append("Memory Device [" + i + "] Speed: ");
			stringBuilder.Append(MemoryDevices[i].Speed);
			stringBuilder.AppendLine(" MHz");
			stringBuilder.AppendLine();
		}
		if (raw != null)
		{
			string text = Convert.ToBase64String(raw);
			stringBuilder.AppendLine("SMBIOS Table");
			stringBuilder.AppendLine();
			for (int j = 0; (double)j < Math.Ceiling((double)text.Length / 64.0); j++)
			{
				stringBuilder.Append(" ");
				for (int k = 0; k < 64; k++)
				{
					int num = (j << 6) | k;
					if (num < text.Length)
					{
						stringBuilder.Append(text[num]);
					}
				}
				stringBuilder.AppendLine();
			}
			stringBuilder.AppendLine();
		}
		return stringBuilder.ToString();
	}
}
