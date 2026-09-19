using System;

namespace MyControlCenter.MySetting.ColorCalibration;

public class NetworkStatusChangedArgs : EventArgs
{
	private bool isAvailable;

	public bool IsAvailable => isAvailable;

	public NetworkStatusChangedArgs(bool isAvailable)
	{
		this.isAvailable = isAvailable;
	}
}
