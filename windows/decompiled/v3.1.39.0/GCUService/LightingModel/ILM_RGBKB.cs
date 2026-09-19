namespace LightingModel;

internal interface ILM_RGBKB
{
	bool ILM_RGBKB_Init();

	RGBKB_Type ILM_RGBKB_GetRGBKeyboardType();

	string ILM_RGBKB_GetFirmwareVersion();

	bool ILM_RGBKB_SetPower(RGBKB_PowerStatus PowerStatus);

	bool ILM_RGBKB_GetPower();

	bool ILM_RGBKB_SetEffectALL(RGBKB_Mode layout_mode, RGBKB_Effect layout_effect, uint layout_light, uint layout_speed, RGBKB_Direction layout_direction, RGBKB_Color layout_colordata, RGBKB_NV_SAVE layout_save, int layout_backgroundcolor = 0, string layout_alphabet = null);

	bool ILM_RGBKB_GetEffectALL(RGBKB_Mode layout_mode, ref RGBKB_Effect layout_effect, ref uint layout_light, ref uint layout_speed, ref RGBKB_Direction layout_direction, ref RGBKB_Color layout_colordata);

	bool ILM_RGBKB_SetEffect(RGBKB_Mode layout_mode, RGBKB_Effect layout_effect);

	bool ILM_RGBKB_GetEffect(RGBKB_Mode layout_mode, ref RGBKB_Effect layout_effect);

	bool ILM_RGBKB_SetBrighntess(uint layout_brightness);

	bool ILM_RGBKB_GetBrighntess(ref uint layout_brightness);

	bool ILM_RGBKB_SetSpeed(uint layout_speed);

	bool ILM_RGBKB_SetColor(RGBKB_Mode layout_mode, RGBKB_Effect layout_effect, RGBKB_Color layout_color);

	bool ILM_RGBKB_SaveLightingLevel(uint layout_light);
}
