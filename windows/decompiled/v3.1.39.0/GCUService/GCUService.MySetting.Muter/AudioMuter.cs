using System;
using System.Runtime.InteropServices;

namespace GCUService.MySetting.Muter;

public class AudioMuter
{
	private IAudioEndpointVolume m_IAEV;

	private float m_Volume;

	public float Volume
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

	public bool Muter
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

	public AudioMuter()
	{
		try
		{
			IMMDeviceEnumerator obj = new MMDeviceEnumeratorComObject() as IMMDeviceEnumerator;
			IMMDevice endpoint = null;
			Marshal.ThrowExceptionForHR(obj.GetDefaultAudioEndpoint(1, 1, out endpoint));
			Guid id = typeof(IAudioEndpointVolume).GUID;
			Marshal.ThrowExceptionForHR(endpoint.Activate(ref id, 23, 0, out m_IAEV));
		}
		catch
		{
		}
	}

	public void Mute()
	{
		m_Volume = Volume;
		Volume = 0f;
	}

	public void UnMute()
	{
		Volume = m_Volume;
	}
}
