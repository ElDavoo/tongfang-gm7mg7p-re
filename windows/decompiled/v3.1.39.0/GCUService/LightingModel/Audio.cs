using System;
using System.Runtime.InteropServices;

namespace LightingModel;

internal static class Audio
{
	private class InitAudioC
	{
		internal InitAudioC()
		{
			try
			{
				IMMDeviceEnumerator obj = new MMDeviceEnumeratorComObject() as IMMDeviceEnumerator;
				IMMDevice endpoint = null;
				Marshal.ThrowExceptionForHR(obj.GetDefaultAudioEndpoint(0, 1, out endpoint));
				Guid id = typeof(IAudioEndpointVolume).GUID;
				Marshal.ThrowExceptionForHR(endpoint.Activate(ref id, 23, 0, out m_IAEV));
			}
			catch
			{
			}
		}
	}

	internal static IAudioEndpointVolume m_IAEV = null;

	private static InitAudioC m_Init = new InitAudioC();

	private static float m_Volume = 0f;

	internal static float Volume
	{
		get
		{
			if (m_IAEV != null)
			{
				float pfLevel = -1f;
				Marshal.ThrowExceptionForHR(m_IAEV.GetMasterVolumeLevelScalar(out pfLevel));
				return pfLevel;
			}
			return 0f;
		}
		set
		{
			if (m_IAEV != null)
			{
				Marshal.ThrowExceptionForHR(m_IAEV.SetMasterVolumeLevelScalar(value, Guid.Empty));
			}
		}
	}

	internal static bool Muter
	{
		get
		{
			if (m_IAEV != null)
			{
				Marshal.ThrowExceptionForHR(m_IAEV.GetMute(out var pbMute));
				return pbMute;
			}
			return false;
		}
		set
		{
			if (m_IAEV != null)
			{
				Marshal.ThrowExceptionForHR(m_IAEV.SetMute(value, Guid.Empty));
			}
		}
	}

	internal static void Mute()
	{
		m_Volume = Volume;
		Volume = 0f;
	}

	internal static void UnMute()
	{
		Volume = m_Volume;
	}
}
