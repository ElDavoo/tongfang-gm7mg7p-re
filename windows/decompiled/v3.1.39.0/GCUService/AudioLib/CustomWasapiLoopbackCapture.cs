using System;
using NAudio.CoreAudioApi;
using NAudio.Wave;

namespace AudioLib;

internal class CustomWasapiLoopbackCapture : WasapiCapture
{
	public override WaveFormat WaveFormat
	{
		get
		{
			return base.WaveFormat;
		}
		set
		{
			throw new InvalidOperationException("WaveFormat cannot be set for WASAPI Loopback Capture");
		}
	}

	public CustomWasapiLoopbackCapture()
		: this(GetDefaultLoopbackCaptureDevice())
	{
	}

	public CustomWasapiLoopbackCapture(MMDevice captureDevice)
		: this(captureDevice, useEventSync: false)
	{
	}

	public CustomWasapiLoopbackCapture(MMDevice captureDevice, bool useEventSync)
		: this(captureDevice, useEventSync, 100)
	{
	}

	public CustomWasapiLoopbackCapture(MMDevice captureDevice, bool useEventSync, int audioBufferMillisecondsLength)
		: base(captureDevice, useEventSync, audioBufferMillisecondsLength)
	{
	}

	public static MMDevice GetDefaultLoopbackCaptureDevice()
	{
		return new MMDeviceEnumerator().GetDefaultAudioEndpoint(DataFlow.Render, Role.Multimedia);
	}

	protected override AudioClientStreamFlags GetAudioClientStreamFlags()
	{
		return AudioClientStreamFlags.Loopback;
	}
}
