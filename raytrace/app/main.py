import os
import io
import numpy as np
import raytrace
from iono import Iono
import h5py
from flask import Flask, request, make_response

if __name__ == '__main__':

    app = Flask(__name__)

    @app.route('/moflof.h5', methods=['GET'])
    def moflof():
        from_lat = float(request.args.get('lat', 41.024))
        from_lon = float(request.args.get('lon', -74.138))
        run_id = request.args.get('run_id', None)
        ts = request.args.get('ts', None)

        from_lat *= np.pi / 180
        from_lon *= np.pi / 180

        iono_url = 'http://localhost:%s/assimilated.h5' % (os.getenv('API_PORT'))
        if run_id is not None and ts is not None:
            iono_url += '?run_id=%s&ts=%s' % (run_id, ts)

        iono = Iono(iono_url)

        to_lat = np.linspace(-90, 90, 181) * np.pi / 180
        to_lon = np.linspace(-180, 180, 361) * np.pi / 180

        to_lon, to_lat = np.meshgrid(to_lon, to_lat)

        from_lat = np.full_like(to_lat, from_lat)
        from_lon = np.full_like(to_lon, from_lon)

        mof_sp, lof_sp = raytrace.mof_lof(iono, from_lat, from_lon, to_lat, to_lon)
        mof_lp, lof_lp = raytrace.mof_lof(iono, from_lat, from_lon, to_lat, to_lon, longpath=True)

        lof_combined = np.fmin(lof_sp, lof_lp)

        mof_sp[mof_sp < lof_sp] = 0.0
        mof_lp[mof_lp < lof_lp] = 0.0
        mof_combined = np.fmax(mof_sp, mof_lp)

        bio = io.BytesIO()
        h5 = h5py.File(bio, 'w')

        h5.create_dataset('/essn/ssn', data=iono.h5['/essn/ssn'])
        h5.create_dataset('/essn/sfi', data=iono.h5['/essn/sfi'])
        h5.create_dataset('/ts', data=iono.h5['/ts'])
        h5.create_dataset('/maps/mof_sp', data=mof_sp, compression='gzip', scaleoffset=3)
        h5.create_dataset('/maps/mof_lp', data=mof_lp, compression='gzip', scaleoffset=3)
        h5.create_dataset('/maps/mof_combined', data=mof_combined, compression='gzip', scaleoffset=3)
        h5.create_dataset('/maps/lof_sp', data=lof_sp, compression='gzip', scaleoffset=3)
        h5.create_dataset('/maps/lof_lp', data=lof_lp, compression='gzip', scaleoffset=3)
        h5.create_dataset('/maps/lof_combined', data=lof_combined, compression='gzip', scaleoffset=3)

        h5.close()

        resp = make_response(bio.getvalue())
        resp.mimetype = 'application/x-hdf5'
        return resp

    app.run(debug=False, host='0.0.0.0', port=int(os.getenv('RAYTRACE_PORT')), threaded=False, processes=8)
