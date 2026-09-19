using System.Runtime.InteropServices;

namespace LightingModel;

[Guid("A95664D2-9614-4F35-A746-DE8DB63617E6")]
[InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
internal interface IMMDeviceEnumerator
{
	int fun1();

	int GetDefaultAudioEndpoint(int dataFlow, int role, out IMMDevice endpoint);
}
