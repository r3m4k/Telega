/* Define to prevent recursive inclusion -------------------------------------*/
#ifndef __SENSORS_KALMAN_PARAMS_HPP
#define __SENSORS_KALMAN_PARAMS_HPP

/* Includes ------------------------------------------------------------------*/
#include "TriaxialData.hpp"

// -----------------------------------------------------------------------------

// Дисперсия значений датчиков, полученные из статических измерений
inline TriaxialData LSM303DLHC_acc_variance = TriaxialData(0.06 * 0.06,   0.06 * 0.06,   0.07 * 0.07);
inline TriaxialData L3GD20_gyro_variance    = TriaxialData(0.019 * 0.019, 0.015 * 0.015, 0.012 * 0.012);
inline TriaxialData LSM303DLHC_mag_variance = TriaxialData(298.0 * 298.0, 211.0 * 211.0, 363.0 * 363.0);

#endif /*   __SENSORS_KALMAN_PARAMS_HPP   */