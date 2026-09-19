using System;
using System.Runtime.InteropServices;

namespace GCUService.MySetting.Muter;

[Guid("D666063F-1587-4E43-81F1-B948E807363F")]
[InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
internal interface IMMDevice
{
	int Activate(ref Guid id, int clsCtx, int activationParams, out IAudioEndpointVolume aev);
}
