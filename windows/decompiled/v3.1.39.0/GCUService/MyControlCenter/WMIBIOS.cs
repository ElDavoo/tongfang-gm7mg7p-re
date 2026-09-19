using System;
using System.Management;
using Utility;

namespace MyControlCenter;

internal class WMIBIOS
{
	public static bool WMIWriteBiosRAM(string Method, ulong Value)
	{
		try
		{
			ManagementObject managementObject = new ManagementObject("root\\WMI", "AcpiODM_Demo.InstanceName='ACPI\\PNP0C14\\2_0'", null);
			ManagementBaseObject methodParameters = managementObject.GetMethodParameters(Method);
			methodParameters["Data"] = Value;
			managementObject.InvokeMethod(Method, methodParameters, null);
			return true;
		}
		catch (ManagementException ex)
		{
			LogCtrl.Write("WMIWriteBiosRAM : Failed" + ex.Message);
			return false;
		}
	}

	public static bool WMIReadBiosRAM(string Method, ulong Value, ref object data)
	{
		try
		{
			ManagementObject managementObject = new ManagementObject("root\\WMI", "AcpiODM_Demo.InstanceName='ACPI\\PNP0C14\\2_0'", null);
			ManagementBaseObject methodParameters = managementObject.GetMethodParameters(Method);
			methodParameters["Data"] = Value;
			ManagementBaseObject managementBaseObject = managementObject.InvokeMethod(Method, methodParameters, null);
			data = managementBaseObject["Return"];
			LogCtrl.Write("WMIReadBiosRAM Return: " + data);
			return true;
		}
		catch (ManagementException ex)
		{
			LogCtrl.Write("WMIReadBiosRAM : Failed" + ex.Message);
			return false;
		}
	}

	public static ulong Combine(byte b7, byte b6, byte b5, byte b4, byte b3, byte b2, byte b1, byte b0)
	{
		return Convert.ToUInt64(BitConverter.ToInt64(new byte[8] { b0, b1, b2, b3, b4, b5, b6, b7 }, 0));
	}
}
